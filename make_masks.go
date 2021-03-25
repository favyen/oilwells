package main

import (
	gomapinfer "github.com/mitroadmaps/gomapinfer/common"
	geocoords "github.com/mitroadmaps/gomapinfer/googlemaps"
	"github.com/mitroadmaps/gomapinfer/image"

	"encoding/json"
	"fmt"
	"io/ioutil"
	"math"
	"strconv"
	"strings"
)

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

	// group polygons by the tiles they intersect
	desiredZoom := 17
	tilePolygons := make(map[[2]int][]gomapinfer.Polygon)
	for _, polygon := range polygons {
		var rect = gomapinfer.EmptyRectangle
		var points []gomapinfer.Point
		for _, point := range polygon {
			ll := gomapinfer.Point{point[0], point[1]}
			p := geocoords.LonLatToMapbox(ll, desiredZoom, [2]int{0, 0})
			rect = rect.Extend(p)
			points = append(points, p)
		}
		sx := int(math.Floor(rect.Min.X/256))
		sy := int(math.Floor(rect.Min.Y/256))
		ex := int(math.Floor(rect.Max.X/256))
		ey := int(math.Floor(rect.Max.Y/256))
		for x := sx; x <= ex; x++ {
			for y := sy; y <= ey; y++ {
				// offset to the top-left corner of this tile
				offset := gomapinfer.Point{float64(x*256), float64(y*256)}
				// compute polygon by subtracting offset
				var poly gomapinfer.Polygon
				for _, point := range points {
					poly = append(poly, point.Sub(offset))
				}
				tilePolygons[[2]int{x, y}] = append(tilePolygons[[2]int{x, y}], poly)
			}
		}
	}

	// create masks corresponding to each downloaded image
	files, err := ioutil.ReadDir("images/")
	if err != nil {
		panic(err)
	}
	for _, fi := range files {
		if !strings.HasSuffix(fi.Name(), ".jpg") {
			continue
		}
		label := strings.Split(fi.Name(), ".jpg")[0]
		parts := strings.Split(label, "_")
		x, _ := strconv.Atoi(parts[0])
		y, _ := strconv.Atoi(parts[1])

		mask := image.MakeGrayImage(256, 256, 0)
		for _, polygon := range tilePolygons[[2]int{x, y}] {
			for i := 0; i < 256; i++ {
				for j := 0; j < 256; j++ {
					if !polygon.Contains(gomapinfer.Point{float64(i), float64(j)}) {
						continue
					}
					mask[i][j] = 255
				}
			}
		}
		image.WriteGrayImage(fmt.Sprintf("images/%d_%d.png", x, y), mask)
	}
}
