import cv2
import os
import glob
import sys
import numpy as np


def dfs(image, x, y, visited):
    if x < 0 or y < 0 or x >= image.shape[1] or y >= image.shape[0] or visited[y][x] or image[y][x][3] == 255:
        return

    r, g, b, a = image[y][x]
    threshold = 127
    if r > threshold and g > threshold and b > threshold:
        image[y][x][3] = 0
    else:
        image[y][x][3] = 255
    visited[y][x] = True
    dfs(image, x+1, y, visited)
    dfs(image, x-1, y, visited)
    dfs(image, x, y+1, visited)
    dfs(image, x, y-1, visited)

def binarize_alpha_channel(image, threshold=128):
    # Check if image has an alpha channel
    if image.shape[2] == 4:
        b, g, r, alpha = cv2.split(image)
    else:
        b, g, r = cv2.split(image)
        alpha = 255 * np.ones(b.shape, dtype=b.dtype)  # Create a fake alpha channel (fully opaque)

    # Binarize the alpha channel
    _, alpha_binary = cv2.threshold(alpha, threshold, 255, cv2.THRESH_BINARY)
    
    # Merge the color channels and the binarized alpha channel back
    binarized_image = cv2.merge([b, g, r, alpha_binary])
    
    return binarized_image

def compact(image):
    # Assuming the image has at least one transparent edge
    starty, startx = 0, 0
    endy, endx = image.shape[0], image.shape[1]
    for y in range(image.shape[0]):
        if not (image[y] == [255, 255, 255, 0]).all():
            starty = y
            break

    for y in range(image.shape[0]-1, -1, -1):
        if not (image[y] == [255, 255, 255, 0]).all():
            endy = y + 1  # Add 1 to include the last line
            break
    for x in range(image.shape[1]):
        if not (image[:, x] == [255, 255, 255, 0]).all():
            startx = x
            break
    for x in range(image.shape[1]-1, -1, -1):
        if not (image[:, x] == [255, 255, 255, 0]).all():
            endx = x + 1  # Add 1 to include the last column
            break
    return image[starty:endy, startx:endx]

def process_images_in_dir(dir_path, output_base_path, threshold=254):
    # Find all png images in the directory
    for file_path in glob.glob(os.path.join(dir_path, '*.png')):
        image = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
        if image is None:
            continue

        # Process image
        # binarized_image = binarize_alpha_channel(image, threshold)
        # compacted_image = compact(binarized_image)
        mask = binarize_alpha_channel(image, 128)
        dfs(image, 0, 0, [[False for _ in range(image.shape[1])] for _ in range(image.shape[0])])
        image = cv2.bitwise_and(image, mask)
        compacted_image = compact(image)

        # Determine output directory and ensure it exists
        output_dir = os.path.join(output_base_path, os.path.basename(dir_path))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Save the image
        output_path = os.path.join(output_dir, os.path.basename(file_path))
        cv2.imwrite(output_path, compacted_image)

# Main script execution
sys.setrecursionlimit(100000)
output_base_path = 'outputs'
current_dir = os.getcwd()
for subdir in next(os.walk(current_dir))[1]:
    process_images_in_dir(os.path.join(current_dir, subdir), output_base_path)


# image = cv2.imread(sys.argv[1], cv2.IMREAD_UNCHANGED)
# mask = binarize_alpha_channel(image, 128)
# dfs(image, 0, 0, [[False for _ in range(image.shape[1])] for _ in range(image.shape[0])])
# image = cv2.bitwise_and(image, mask)
# cv2.imwrite(sys.argv[2], image)
