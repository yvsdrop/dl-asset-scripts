#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import os
import UnityPy
from PIL import Image

def unpack_asset(file_path):
  image_map = {}
  composite_data = {}

  env = UnityPy.load(file_path)
  for obj in env.objects:
    if obj.type == 'Texture2D':
      data = obj.read()
      image_map[data.name] = data.image
    elif obj.type == 'MonoBehaviour':
      composite_data = obj.read().type_tree

  # First save the base image
  base_name = composite_data['name']
  output_dir = os.path.join(os.path.dirname(file_path), base_name)
  os.makedirs(output_dir, exist_ok=True)

  base_rect = composite_data['basePartsData']['rect']
  base_img_name = f'{base_name}_base'
  base_img = merge_image(image_map, base_img_name, f'{base_img_name}_alpha')
  base_img = base_img.crop((base_rect['x'], base_rect['y'], base_rect['x'] + base_rect['width'], base_rect['y'] + base_rect['height']))
  base_img.save(os.path.join(output_dir, base_img_name + '.png'))

  # Then save the parts
  # Some indices are repeated, map first to avoid duplicate work
  partsAlphaMap = {
    str(p['colorIndex']).zfill(3): p['alphaIndex']
    for p in composite_data['partsTextureIndexTable']
  }
  for index, alphaIndex in partsAlphaMap.items():
    img_name = f'{base_name}_parts_c{index}'
    img = merge_image(image_map, img_name, f'{base_name}_parts_a{alphaIndex:03}_alpha')
    img.save(os.path.join(output_dir, f'{img_name}.png'))


def merge_image(image_map, img_name, alpha_name):
  try:
    Y = image_map[img_name + '_Y'].convert('RGBA').split()[-1]
    Cb = image_map[img_name + '_Cb'].convert('L').resize(Y.size, Image.ANTIALIAS)
    Cr = image_map[img_name + '_Cr'].convert('L').resize(Y.size, Image.ANTIALIAS)
    img = Image.merge('YCbCr', (Y, Cb, Cr)).convert('RGBA')
  except KeyError:
    print('Missing image data for ' + img_name)
    return None

  try:
    a = image_map[alpha_name].convert('L')
    img.putalpha(a)
  except KeyError:
    pass # Image doesn't have an alpha channel, this is fine
  return img


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Split story image bundles into expressions')
  parser.add_argument('bundle', type=str, help='input bundle')
  args = parser.parse_args()

  unpack_asset(args.bundle)