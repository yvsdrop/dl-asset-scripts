#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import os
import UnityPy
from PIL import Image
from collections import defaultdict

def unpack_asset(file_path, use_position, make_html):
  image_map = {}
  composite_data = {}

  env = UnityPy.load(file_path)
  for obj in env.objects:
    if obj.type == 'Texture2D':
      data = obj.read()
      image_map[data.name] = data.image
    elif obj.type == 'MonoBehaviour':
      composite_data = obj.read().read_type_tree()

  base_name = composite_data['name']
  partsAlphaMap = {
    str(p['colorIndex']).zfill(3): str(p['alphaIndex']).zfill(3)
    for p in composite_data['partsTextureIndexTable']
  }
  alpha_map = defaultdict(list)

  # First save the base image
  output_dir = os.path.join(os.path.dirname(file_path), base_name)
  os.makedirs(output_dir, exist_ok=True)
  base_img_name = f'{base_name}_base'
  base_img = merged_image(image_map, base_img_name, f'{base_img_name}_alpha')
  base_img.save(os.path.join(output_dir, base_img_name + '.png'))

  if use_position:
    parts_position = composite_data['partsDataTable'][0]['position']
    parts_size = composite_data['partsDataTable'][0]['size']
    part_position = (int(parts_position['x'] - (parts_size['x'] / 2)), int(parts_position['y'] - (parts_size['y'] / 2)))
    # Create blank template for pasting parts onto
    base_img = Image.new('RGBA', base_img.size, (0, 0, 0, 0))

  for index, alphaIndex in partsAlphaMap.items():
    img_name = f'{base_name}_parts_c{index}'
    alpha_map[alphaIndex].append(index)
    img = merged_image(image_map, img_name, f'{base_name}_parts_a{alphaIndex}_alpha')

    if use_position:
      base_img.paste(img, part_position)
      base_img.save(os.path.join(output_dir, img_name + '.png'))
    else:
      img.save(os.path.join(output_dir, img_name + '.png'))
    # print(img_name)

  if make_html:
    with open(os.path.join(output_dir, base_name + '.html'), 'w') as html_file:
      images = []
      part_options = []
      for alphaIndex, parts in alpha_map.items():
        images.append(f'<div id="parts{alphaIndex}_images">' + ''.join(
          (IMG_TEMPLATE.format(name=p, src=f'{base_name}_parts_c{p}') for p in parts)
        ) + '</div>')
        part_options.append(
          PART_TEMPLATE.format(part_num=alphaIndex, options=''.join(
            (OPTION_TEMPLATE.format(p) for p in parts)
          )))
      
      html_file.write(HTML_TEMPLATE.format(
        title=base_name,
        parts_options=''.join(part_options),
        base_img=base_img_name,
        images=''.join(images)
      ))


def merged_image(image_map, img_name, alpha_name):
  Y = image_map[img_name + '_Y'].convert('RGBA').split()[-1]
  Cb = image_map[img_name + '_Cb'].convert('L').resize(Y.size, Image.ANTIALIAS)
  Cr = image_map[img_name + '_Cr'].convert('L').resize(Y.size, Image.ANTIALIAS)
  a = image_map[alpha_name].convert('L')
  img = Image.merge('YCbCr', (Y, Cb, Cr)).convert('RGBA')
  img.putalpha(a)
  return img


HTML_TEMPLATE = (
  '<!DOCTYPE html>'
  '<head>'
  '<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.0/css/bootstrap.min.css">'
  '<script src="https://code.jquery.com/jquery-3.5.1.slim.min.js" crossorigin="anonymous"></script>'
  '<script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.0/js/bootstrap.min.js"></script>'
  '<style>.images img {{position:absolute}}</style>'
  '<title>{title}</title>'
  '</head>'
  '<body class="container" style="padding:40px">'
    '{parts_options}'
    '<div class="images" style="position:relative">'
      '<img src="{base_img}.png">'
      '{images}'
    '</div>'
  '<script>'
    '''$('.part-selector').change(function() {{
      $('#' + this.id + '_images img').hide();
      $('img#' + this.value).show();
    }});'''
  '</script>'
  '</body>'
  '</html>'
)
PART_TEMPLATE = (
  'Part {part_num}:'
  '<select class="form-control part-selector" id="parts{part_num}">'
    '<option disabled selected value></option>'
    '{options}'
  '</select>'
)
OPTION_TEMPLATE = '<option value="{0}">{0}</option>'
IMG_TEMPLATE = '<img id="{name}" src="{src}.png" style="display:none">'


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Split story image bundles into expressions')
  parser.add_argument('bundle', type=str, help='input bundle')
  parser.add_argument('-pos', type=bool, help='position the expressions relative to the overall image (default: True)', default=True)
  parser.add_argument('-html', type=bool, help='create an HTML output (default: True)', default=True)
  args = parser.parse_args()

  unpack_asset(args.bundle, use_position=args.pos, make_html=args.html)
