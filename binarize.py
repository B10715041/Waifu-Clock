import cv2
from sys import argv

def binarize_alpha_channel(image_path, threshold=128):
    # Load the image with alpha channel
    image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    
    if image is None:
        raise ValueError("Image not found or unable to load image.")

    # Split the image into its color and alpha channels
    b, g, r, alpha = cv2.split(image)
    
    # Binarize the alpha channel
    _, alpha_binary = cv2.threshold(alpha, threshold, 255, cv2.THRESH_BINARY)
    
    # Merge the color channels and the binarized alpha channel back
    binarized_image = cv2.merge([b, g, r, alpha_binary])
    
    return binarized_image

def save_image(image, output_path):
    cv2.imwrite(output_path, image)


# Example usage
input_image_path = argv[1]
output_image_path = argv[2]

threshold_value = 254
if len(argv) > 3:
    threshold_value = int(argv[3])


binarized_image = binarize_alpha_channel(input_image_path, threshold_value)
save_image(binarized_image, output_image_path)

