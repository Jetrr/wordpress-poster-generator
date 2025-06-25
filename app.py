import random
import os
from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import re

app = Flask(__name__, static_folder='static')

def hex_to_rgba(hex_str, alpha=255):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join(2 * c for c in hex_str)
    rgb = tuple(int(hex_str[i:i + 2], 16) for i in (0, 2, 4))
    return rgb + (alpha,)

def wrap_text(text, font, max_width):
    words = text.strip().split()
    lines = []
    current = ""
    for word in words:
        test = word if current == "" else current + " " + word
        bbox = font.getbbox(test)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

def parse_heading_to_lines(heading, default_color):
    lines = []
    for line_part in heading.split(','):
        tokens = re.split(r'(\[#(?:[A-Fa-f0-9]{3,6})\])', line_part.strip())
        current_color = default_color
        words = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            hex_match = re.match(r'\[#([A-Fa-f0-9]{3,6})\]', token)
            if hex_match:
                current_color = "#" + hex_match.group(1)
                i += 1
                if i < len(tokens) and tokens[i].strip():
                    next_word = tokens[i].strip().split()[0]
                    words.append((next_word, current_color))
                    rest = tokens[i].strip()[len(next_word):].strip()
                    if rest:
                        for rest_w in rest.split():
                            words.append((rest_w, default_color))
                current_color = default_color
            elif token.strip():
                for word in token.strip().split():
                    words.append((word, current_color))
            i += 1
        if words:
            lines.append(words)
    return lines

class PosterTemplate:
    def __init__(self, base, company_name, main_heading, subheading, font_color):
        self.base = base
        self.company_name = company_name.lower()
        self.main_heading = main_heading
        self.subheading = subheading
        self.font_color = font_color or "#1e1e1e"
        self.logo_path = os.path.join(base, "static", f"{self.company_name}.png")
        if not os.path.exists(self.logo_path):
            raise FileNotFoundError(f"Logo file {self.company_name}.png not found.")

class ClassicPosterTemplate(PosterTemplate):
    def generate(self):
        characters_dir = os.path.join(self.base, 'static', 'characters', self.company_name)
        character_imgs = [
            os.path.join(characters_dir, img)
            for img in os.listdir(characters_dir)
            if img.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
        if not character_imgs:
            raise Exception(f"No character images found for company {self.company_name}!")
        chosen_img_path = random.choice(character_imgs)
        png = Image.open(chosen_img_path).convert("RGBA")

        main_heading_lines = parse_heading_to_lines(self.main_heading, self.font_color)
        main_font_path = os.path.join(self.base, 'static', 'GolosText-Regular.ttf')
        main_font_bold_path = os.path.join(self.base, 'static', 'GolosText-Bold.ttf')
        subheading_font_path = main_font_path

        output_size = (1425, 753)
        main_font_size = 62
        subheading_font_size = 36
        main_font = ImageFont.truetype(main_font_path, main_font_size)
        main_font_bold = ImageFont.truetype(main_font_bold_path, main_font_size)
        subheading_font = ImageFont.truetype(subheading_font_path, subheading_font_size)

        # Character placement & scaling
        orig_png_w, orig_png_h = png.size
        scaled_height = int(0.8 * output_size[1])
        aspect_ratio = orig_png_w / orig_png_h
        scaled_width = int(aspect_ratio * scaled_height)
        png = png.resize((scaled_width, scaled_height), Image.LANCZOS)
        bg = Image.new("RGBA", output_size, (255, 255, 255, 255))
        right_x = output_size[0] - scaled_width
        top_y = int((output_size[1] - scaled_height) // 2)
        bg.paste(png, (right_x, top_y), png)

        LEFT_MARGIN = 80
        max_icon_width = 164
        max_icon_height = 164
        icon = Image.open(self.logo_path).convert("RGBA")
        icon_w, icon_h = icon.size
        scale = min(max_icon_width / icon_w, max_icon_height / icon_h)
        new_icon_w = int(icon_w * scale)
        new_icon_h = int(icon_h * scale)
        icon = icon.resize((new_icon_w, new_icon_h), Image.LANCZOS)
        icon_x = LEFT_MARGIN
        icon_y = LEFT_MARGIN
        bg.paste(icon, (icon_x, icon_y), icon)

        draw = ImageDraw.Draw(bg)
        text_x = LEFT_MARGIN
        max_text_width = right_x - text_x

        fixed_line_height = main_font_bold.getbbox("Ay")[3] - main_font_bold.getbbox("Ay")[1]
        line_spacing = 10
        main_heading_lines_count = len(main_heading_lines)
        main_block_height = main_heading_lines_count * fixed_line_height + (main_heading_lines_count - 1) * line_spacing

        subheading_lines = wrap_text(self.subheading, subheading_font, max_text_width)
        subheading_line_height = subheading_font.getbbox("Ay")[3] - subheading_font.getbbox("Ay")[1]
        sub_block_height = len(subheading_lines) * subheading_line_height

        gap_between_heading_and_sub = 44  # fixed gap
        total_text_block_height = main_block_height + gap_between_heading_and_sub + sub_block_height

        image_height = output_size[1]
        vertical_margin = 40
        usable_height = image_height - 2 * vertical_margin
        start_y = vertical_margin + (usable_height - total_text_block_height) // 2

        y_cursor = start_y
        for line in main_heading_lines:
            line_x = text_x
            for word, color in line:
                font = main_font_bold
                bbox = font.getbbox(word)
                word_width = bbox[2] - bbox[0]
                draw.text((line_x, y_cursor), word, font=font, fill=hex_to_rgba(color))
                line_x += word_width + 12
            y_cursor += fixed_line_height + line_spacing

        subheading_top = y_cursor + gap_between_heading_and_sub - line_spacing
        for i, line in enumerate(subheading_lines):
            draw.text(
                (text_x, subheading_top + i * subheading_line_height),
                line,
                font=subheading_font,
                fill=hex_to_rgba(self.font_color),
            )

        return bg

class RightImageBackgroundPosterTemplate(PosterTemplate):
    def generate(self):
        output_size = (1425, 753)
        bg_folder = os.path.join(self.base, 'static', 'background', self.company_name)
        bg_img_path = os.path.join(bg_folder, f'{self.company_name}-background.png')

        if os.path.exists(bg_img_path):
            bg = Image.open(bg_img_path).convert("RGBA").resize(output_size, Image.LANCZOS)
        else:
            bg = Image.new("RGBA", output_size, (255, 255, 255, 255))

        characters_dir = os.path.join(self.base, 'static', 'characters', self.company_name)
        character_imgs = [
            os.path.join(characters_dir, img)
            for img in os.listdir(characters_dir)
            if img.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
        if not character_imgs:
            raise Exception(f"No character images found for company {self.company_name}!")
        chosen_img_path = random.choice(character_imgs)
        char_img = Image.open(chosen_img_path).convert("RGBA")
        char_max_height = int(0.85 * output_size[1])
        aspect = char_img.width / char_img.height
        new_char_width = int(char_max_height * aspect)
        char_img = char_img.resize((new_char_width, char_max_height), Image.LANCZOS)
        right_x = output_size[0] - new_char_width - 40
        top_y = int((output_size[1] - char_max_height) // 2)
        bg.paste(char_img, (right_x, top_y), char_img)
        # Logo at top left (=== CHANGED PADDING HERE ===)
        LEFT_MARGIN = 80
        max_icon_width = 164
        max_icon_height = 164
        logo = Image.open(self.logo_path).convert("RGBA")
        icon_w, icon_h = logo.size
        icon_scale = min(max_icon_width / icon_w, max_icon_height / icon_h)
        icon_new_w = int(icon_w * icon_scale)
        icon_new_h = int(icon_h * icon_scale)
        logo = logo.resize((icon_new_w, icon_new_h), Image.LANCZOS)
        icon_x = LEFT_MARGIN
        icon_y = LEFT_MARGIN
        bg.paste(logo, (icon_x, icon_y), logo)

        main_heading_lines = parse_heading_to_lines(self.main_heading, self.font_color)
        main_font_path = os.path.join(self.base, 'static', 'GolosText-Regular.ttf')
        main_font_bold_path = os.path.join(self.base, 'static', 'GolosText-Bold.ttf')
        subheading_font_path = main_font_path
        main_font_size = 62
        subheading_font_size = 36
        main_font = ImageFont.truetype(main_font_path, main_font_size)
        main_font_bold = ImageFont.truetype(main_font_bold_path, main_font_size)
        subheading_font = ImageFont.truetype(subheading_font_path, subheading_font_size)

        draw = ImageDraw.Draw(bg)
        text_x = LEFT_MARGIN
        text_y = 200
        max_text_width = right_x - text_x - 40

        fixed_line_height = main_font_bold.getbbox("Ay")[3] - main_font_bold.getbbox("Ay")[1]
        line_spacing = 10

        y_cursor = text_y
        for line in main_heading_lines:
            line_x = text_x
            for word, color in line:
                font = main_font_bold
                bbox = font.getbbox(word)
                word_width = bbox[2] - bbox[0]
                draw.text((line_x, y_cursor), word, font=font, fill=hex_to_rgba(color))
                line_x += word_width + 12
            y_cursor += fixed_line_height + line_spacing

        subheading_lines = wrap_text(self.subheading, subheading_font, max_text_width)
        subheading_line_height = subheading_font.getbbox("Ay")[3] - subheading_font.getbbox("Ay")[1]
        subheading_top = y_cursor + 44
        for i, line in enumerate(subheading_lines):
            draw.text(
                (text_x, subheading_top + i * subheading_line_height),
                line,
                font=subheading_font,
                fill=hex_to_rgba(self.font_color)
            )
        return bg

### === Factory ===
class PosterTemplateFactory:
    templates = {
        'classic': ClassicPosterTemplate,
        '1': ClassicPosterTemplate,
        'rightimage': RightImageBackgroundPosterTemplate,
        '2': RightImageBackgroundPosterTemplate,
    }

    @classmethod
    def get_template(cls, template_id, *args, **kwargs):
        tpl = cls.templates.get(str(template_id).lower())
        if not tpl:
            raise ValueError("Invalid poster_template_id")
        return tpl(*args, **kwargs)

@app.route('/generate', methods=['POST'])
def generate():
    try:
        company_name = request.form.get('company_name', '').strip().lower()
        main_heading = request.form.get('poster_main_heading', '').strip()
        subheading = request.form.get('poster_subheading', '').strip()
        font_color = request.form.get('font_color', '#1e1e1e')
        template_id = request.form.get('poster_template_id', 'classic').strip().lower()
        if not company_name or not main_heading or not template_id:
            return jsonify({"error": "Fields 'company_name', 'poster_main_heading', and 'poster_template_id' are required."}), 400
        base = os.path.dirname(os.path.abspath(__file__))
        poster = PosterTemplateFactory.get_template(
            template_id,
            base, company_name, main_heading, subheading, font_color
        ).generate()
        out_io = BytesIO()
        poster.convert("RGB").save(out_io, format="PNG")
        out_io.seek(0)
        return send_file(out_io, mimetype='image/png')
    except FileNotFoundError as fnf:
        return jsonify({'error': str(fnf)}), 500
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def hello():
    return "Poster API Running!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)