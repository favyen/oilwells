package main

import (
	gomapinfer "github.com/mitroadmaps/gomapinfer/common"
	geocoords "github.com/mitroadmaps/gomapinfer/googlemaps"
	"fmt"
	"os"
	"strconv"
)

func main() {
	x, _ := strconv.Atoi(os.Args[1])
	y, _ := strconv.Atoi(os.Args[2])
	ll := geocoords.MapboxToLonLat(gomapinfer.Point{0, 0}, 17, [2]int{x, y})
	fmt.Printf("%v,%v\n", ll.Y, ll.X)
}
