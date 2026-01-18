import sys
import os
import math
import argparse

def parse_obj(filename):
    """Parses OBJ file and extracts unique edges and vertices."""
    vertices = []
    edges = set()
    
    if not os.path.exists(filename):
        print(f"Error: File {filename} not found.")
        sys.exit(1)

    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('v '):
                vertices.append([float(x) for x in line.split()[1:4]])
            elif line.startswith('f '):
                # Handle v/t/n format by splitting on '/'
                face = [int(x.split('/')[0]) - 1 for x in line.split()[1:]]
                # Convert face into unique edges
                for i in range(len(face)):
                    v1, v2 = face[i], face[(i + 1) % len(face)]
                    edges.add(tuple(sorted((v1, v2))))
    
    # Normalize vertices to signed 12-bit range (-2047 to 2047)
    max_val = max(max(abs(coord) for coord in v) for v in vertices)
    scale = 2047 / max_val
    scaled_vertices = [[round(c * scale) for c in v] for v in vertices]
    
    return scaled_vertices, list(edges)

def dist_sq(p1, p2):
    """Calculates squared Euclidean distance between two points."""
    return sum((a - b) ** 2 for a, b in zip(p1, p2))

def find_optimized_path(vertices, edges):
    """
    Finds a path that visits every edge exactly once. 
    When stuck, it jumps to the nearest available vertex of an unvisited edge.
    """
    remaining_edges = set(edges)
    path = []
    
    # Start at the first vertex of the first edge
    current_v = edges[0][0]
    path.append(current_v)

    while remaining_edges:
        next_v = None
        
        # 1. Look for a connected edge from the current vertex
        for edge in list(remaining_edges):
            if current_v in edge:
                next_v = edge[1] if edge[0] == current_v else edge[0]
                remaining_edges.remove(edge)
                break
        
        if next_v is not None:
            path.append(next_v)
            current_v = next_v
        else:
            # 2. JUMP: No connected edges left. Find the nearest unvisited vertex.
            best_dist = float('inf')
            best_edge = None
            best_start_v = None
            target_v = None

            for edge in remaining_edges:
                # Check distance to both ends of the unvisited edge
                d0 = dist_sq(vertices[current_v], vertices[edge[0]])
                d1 = dist_sq(vertices[current_v], vertices[edge[1]])
                
                if d0 < best_dist:
                    best_dist = d0
                    best_edge = edge
                    best_start_v = edge[0]
                    target_v = edge[1]
                if d1 < best_dist:
                    best_dist = d1
                    best_edge = edge
                    best_start_v = edge[1]
                    target_v = edge[0]

            if best_edge:
                # Add the 'jump' point to the path
                path.append(best_start_v)
                # Then add the end of that edge
                path.append(target_v)
                remaining_edges.remove(best_edge)
                current_v = target_v
                
    return path

def generate_header(filename, vertices, path):
    """Generates a C++ header file with the point data."""
    base_name = os.path.splitext(os.path.basename(filename))[0].upper()
    
    header = [
        f"#ifndef {base_name}_MESH_H",
        f"#define {base_name}_MESH_H",
        "",
        "#include <stdint.h>",
        "",
        "struct Point3D {",
        "    int16_t x, y, z;",
        "};",
        "",
        f"const uint32_t {base_name}_PATH_COUNT = {len(path)};",
        f"const Point3D {base_name}_PATH[] = {{"
    ]
    
    for idx in path:
        v = vertices[idx]
        header.append(f"    {{{v[0]}, {v[1]}, {v[2]}}},")
        
    header.append("};")
    header.append("")
    header.append("#endif")
    
    return "\n".join(header)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Convert OBJ 3D model to optimized C++ header with edge path'
    )
    parser.add_argument('input', help='Input OBJ file path')
    parser.add_argument('-o', '--output', 
                        help='Output header file path (default: ../data/mesh_data.h)')
    
    args = parser.parse_args()
    
    # Set default output path if not provided
    if args.output is None:
        args.output = os.path.join(os.path.dirname(__file__), '..', 'data', 'mesh_data.h')
    
    try:
        v_data, e_data = parse_obj(args.input)
        final_path = find_optimized_path(v_data, e_data)
        
        header_content = generate_header(args.input, v_data, final_path)
        
        with open(args.output, "w") as f:
            f.write(header_content)
            
        print(f"--- Processing Complete ---")
        print(f"Input: {args.input}")
        print(f"Unique Edges: {len(e_data)}")
        print(f"Path Points:  {len(final_path)}")
        print(f"Header saved to: {args.output}")
    except FileNotFoundError:
        print(f"Error: File '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)