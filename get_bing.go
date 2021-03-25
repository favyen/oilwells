package main

import (
	gomapinfer "github.com/mitroadmaps/gomapinfer/common"
	geocoords "github.com/mitroadmaps/gomapinfer/googlemaps"

	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"strconv"
	"sync"
	"time"
)

const URL = "https://ecn.t%s.tiles.virtualearth.net/tiles/a%s.jpeg?g=587&mkt=en-gb&n=z"
var SERVERS []string = []string{"1", "2", "3", "4"}

func toBitString(x int, n int) string {
	s := ""
	for x > 0 {
		s = strconv.Itoa(x % 2) + s
		x /= 2
	}
	for len(s) < n {
		s = "0" + s
	}
	return s
}

var binToBase4 map[string]string = map[string]string{
	"00": "0",
	"01": "1",
	"10": "2",
	"11": "3",
}

func GetSatelliteImage(server string, zoom int, x int, y int, fname string) {
	// get bing quadkey
	// 1) convert x/y to bit strings
	// 2) interleave the bit strings
	// 3) convert to base 4
	xstr := toBitString(x, zoom)
	ystr := toBitString(y, zoom)
	quadkey := ""
	for i := 0; i < zoom; i++ {
		quadkey += binToBase4[string(ystr[i]) + string(xstr[i])]
	}

	url := fmt.Sprintf(URL, server, quadkey)
	fmt.Println(url)
	resp, err := http.Get(url)
	if err != nil {
		panic(err)
	}
	if resp.StatusCode != 200 || resp.Header.Get("Content-Type") != "image/jpeg" {
		if resp.StatusCode == 500 {
			fmt.Printf("warning: got 500 on %s (retrying later)\n", url)
			time.Sleep(5 * time.Second)
			GetSatelliteImage(server, zoom, x, y, fname)
		} else {
			var errdesc string
			if resp.Header.Get("Content-Type") != "image/jpeg" {
				if bytes, err := ioutil.ReadAll(resp.Body); err == nil {
					errdesc = string(bytes)
				}
			}
			panic(fmt.Errorf("got status code %d (errdesc=%s)", resp.StatusCode, errdesc))
		}
	}
	imBytes, err := ioutil.ReadAll(resp.Body)
	resp.Body.Close()
	if err != nil {
		panic(err)
	}
	if err := ioutil.WriteFile(fname, imBytes, 0644); err != nil {
		panic(err)
	}
}

func main() {
	// load polygons
	var polygons [][][2]float64
	bytes, err := ioutil.ReadFile("pad_site_polygons.json")
	if err != nil {
		panic(err)
	}
	if err := json.Unmarshal(bytes, &polygons); err != nil {
		panic(err)
	}

	// compute which mapbox tiles are needed
	desiredZoom := 17
	wantedTiles := make(map[[2]int]bool)
	for _, polygon := range polygons {
		for _, point := range polygon {
			ll := gomapinfer.Point{point[0], point[1]}
			tile := geocoords.LonLatToMapboxTile(ll, desiredZoom)
			for _, ox := range []int{-1, 0, 1} {
				for _, oy := range []int{-1, 0, 1} {
					wantedTiles[[2]int{tile[0]+ox, tile[1]+oy}] = true
				}
			}
		}
	}

	// determine which ones haven't been downloaded yet
	var neededTiles [][2]int
	for tile := range wantedTiles {
		fname := fmt.Sprintf("images/%d_%d.jpg", tile[0], tile[1])
		if _, err := os.Stat(fname); err == nil {
			continue
		}
		neededTiles = append(neededTiles, tile)
	}

	fmt.Printf("found %d wanted tiles, %d still needed\n", len(wantedTiles), len(neededTiles))

	ch := make(chan [2]int)
	var wg sync.WaitGroup
	for i := 0; i < len(SERVERS); i++ {
		wg.Add(1)
		go func(server string) {
			defer wg.Done()
			for tile := range ch {
				fname := fmt.Sprintf("images/%d_%d.jpg", tile[0], tile[1])
				fmt.Printf("creating %s\n", fname)
				GetSatelliteImage(server, desiredZoom, tile[0], tile[1], fname)
			}
		}(SERVERS[i])
	}

	for _, tile := range neededTiles {
		ch <- tile
	}
	close(ch)
	wg.Wait()
}
