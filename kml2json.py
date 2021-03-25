import json
import sys

src_fname = sys.argv[1]
dst_fname = sys.argv[2]

with open(src_fname, 'r') as f:
    lines = f.readlines()

polygons = []

for i, line in enumerate(lines):
    if '<coordinates>' not in line:
        continue
    polygon = []
    for line in lines[i+1:]:
        if '</coordinates>' in line:
            break
        points = line.strip().split(',')
        polygon.append([float(points[0]), float(points[1])])
    polygons.append(polygon)

with open(dst_fname, 'w') as f:
    json.dump(polygons, f)
