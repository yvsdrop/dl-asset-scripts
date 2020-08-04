#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import os
import UnityPy
from PIL import Image
from collections import defaultdict

def unpack_asset(file_path, make_html):
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
    str(p['colorIndex']).zfill(3): (str(p['alphaIndex']).zfill(3) if p['alphaIndex'] >= 0 else 'noalpha')
    for p in composite_data['partsTextureIndexTable']
  }

  # First save the base image
  output_dir = os.path.join(os.path.dirname(file_path), base_name)
  os.makedirs(output_dir, exist_ok=True)
  base_img_name = f'{base_name}_base'
  base_img = merge_image_alpha(image_map, base_img_name, f'{base_img_name}_alpha')
  base_img.save(os.path.join(output_dir, base_img_name + '.png'))

  parts_position = composite_data['partsDataTable'][0]['position']
  parts_size = composite_data['partsDataTable'][0]['size']
  part_position = (int(parts_position['x'] - (parts_size['x'] / 2)), int(parts_position['y'] - (parts_size['y'] / 2)))

  if not make_html:
    # Create blank template for pasting parts onto
    base_img = Image.new('RGBA', base_img.size, (0, 0, 0, 0))

  for index, alphaIndex in partsAlphaMap.items():
    img_name = f'{base_name}_parts_c{index}'
    if alphaIndex == 'noalpha':
      img = merge_image(image_map, img_name)
    else:
      img = merge_image_alpha(image_map, img_name, f'{base_name}_parts_a{alphaIndex}_alpha')

    if not make_html:
      base_img.paste(img, part_position)
      base_img.save(os.path.join(output_dir, img_name + '.png'))
    else:
      img.save(os.path.join(output_dir, img_name + '.png'))
    # print(img_name)

  if make_html:
    images = []
    for index in partsAlphaMap:
      images.append(IMG_TEMPLATE.format(id=index, base_name=base_name))

    with open(os.path.join(output_dir, 'index.html'), 'w') as html_file:
      html_file.write(HTML_TEMPLATE.format(
        title=base_name,
        base_img=base_img_name,
        width=base_img.size[0],
        height=base_img.size[1],
        pos_x=part_position[0],
        pos_y=part_position[1],
        parts=''.join(images)
      ))


def merge_image(image_map, img_name):
  Y = image_map[img_name + '_Y'].convert('RGBA').split()[-1]
  Cb = image_map[img_name + '_Cb'].convert('L').resize(Y.size, Image.ANTIALIAS)
  Cr = image_map[img_name + '_Cr'].convert('L').resize(Y.size, Image.ANTIALIAS)
  img = Image.merge('YCbCr', (Y, Cb, Cr)).convert('RGBA')
  return img


def merge_image_alpha(image_map, img_name, alpha_name):
  a = image_map[alpha_name].convert('L')
  img = merge_image(image_map, img_name)
  img.putalpha(a)
  return img


HTML_TEMPLATE = (
  '<!DOCTYPE html>'
  '<head>'
  '<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.0/css/bootstrap.min.css">'
  '<script src="https://code.jquery.com/jquery-3.5.1.slim.min.js" crossorigin="anonymous"></script>'
  '<script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.0/js/bootstrap.min.js"></script>'
  '<style>'
    '.part {{padding:6px;margin:2px;border-radius:4px;cursor:pointer}}'
    '.part:hover {{background:rgba(0,0,0,.2)}}'
    '.part.selected {{background:lightskyblue}}'
    '.part img {{border-radius:4px;max-width:100px}}'
  '</style>'
  '<title>{title}</title>'
  '</head>'
  '<body onload="onload()" style="display:flex">'
    '<img id="base-img" src="{base_img}.png" style="display:none">'
    '<div style="height:100vh;padding:2em;overflow-y:auto;flex:1 0 415px;max-width:max(415px, 36vw);border-right:1px solid #ccc;">'
      '<h5>Expressions<button id="reset-btn" class="btn btn-outline-primary" style="margin-left:1em;">Reset</button></h5>'
      '<div style="display:flex;flex-flow:row wrap;margin:0 -10px">{parts}</div>'
    '</div>'
    '<canvas id="canvas" width="{width}" height="{height}" style="flex:none;align-self:start"></canvas>'
    '<script>'
    '''let ctx, canvas, base_image;
    function onload() {{
      canvas = $('#canvas')[0];
      ctx = canvas.getContext('2d');
      base_image = $('#base-img')[0];
      reset();

      $('.part').click(function() {{
        reset();
        $(this).toggleClass('selected');
        $('.selected').each(function() {{
          ctx.drawImage(this.firstChild, {pos_x}, {pos_y});
        }});
      }});
      $('#reset-btn').click(function() {{
        reset();
        $('.selected').each(function() {{
          $(this).removeClass('selected');
        }});
      }});
    }}
    function reset() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(base_image, 0, 0);
    }}'''
    '</script>'
  '</body>'
  '</html>'
)
IMG_TEMPLATE = '<a class="part" id="{id}"><img src="{base_name}_parts_c{id}.png"></a>'


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Split story image bundles into expressions')
  parser.add_argument('bundle', type=str, help='input bundle')
  parser.add_argument('-html', type=bool, help='create an HTML output (default: True)', default=True)
  args = parser.parse_args()

  unpack_asset(args.bundle, make_html=args.html)
