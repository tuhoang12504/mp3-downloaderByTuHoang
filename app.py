from flask import Flask, render_template, request, send_file, after_this_request
import yt_dlp
import os
import re
import threading

app = Flask(__name__)
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/download', methods=['POST'])
def download():
    link_yt = request.form['link_youtube'].strip()
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(link_yt, download=False)
            video_title = info.get('title', 'Không có tiêu đề')
            formats = info.get('formats', [])
            thumbnail_url = info.get('thumbnail', '')
            clean_title = sanitize_filename(video_title)

            available_formats = []
            seen = set()

            for f in formats:
                ext = f.get('ext')
                format_id = f.get('format_id')
                filesize = f.get('filesize') or f.get('filesize_approx') or 0
                vcodec = f.get('vcodec')
                abr = f.get('abr', 0)

                if not format_id or vcodec != 'none' or ext not in ['m4a', 'webm']:
                    continue

                key = (ext, format_id)
                if key in seen:
                    continue
                seen.add(key)

                available_formats.append({
                    'format_id': format_id,
                    'ext': 'mp3',
                    'resolution': f"{int(abr)} kbps" if abr else "Không rõ",
                    'file_size': f"{round(filesize / 1024 / 1024, 2)} MB" if filesize else "Không rõ"
                })

        return render_template(
            'home.html',
            formats=available_formats,
            title=clean_title,
            link=link_yt,
            thumbnail=thumbnail_url
        )

    except Exception as e:
        return f"Lỗi: {str(e)}"

@app.route('/fetch', methods=['POST'])
def fetch():
    link = request.form.get('link')
    format_id = request.form.get('format_id')
    title = sanitize_filename(request.form.get('title', 'audio'))
    output_path = os.path.join(DOWNLOAD_FOLDER, f"{title}.mp3")

    ydl_opts = {
        'format': format_id,
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        'quiet': True,
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link)
            original_path = ydl.prepare_filename(info)
            filepath = re.sub(r'\.\w+$', '.mp3', original_path)

        if not os.path.isfile(filepath):
            return f"Không tìm thấy file: {filepath}"

        @after_this_request
        def cleanup(response):
            def delete_file():
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"Không thể xóa file: {e}")
            threading.Timer(5.0, delete_file).start()
            return response

        return send_file(filepath, as_attachment=True)

    except Exception as e:
        return f'Lỗi tải MP3: {str(e)}'

if __name__ == '__main__':
    app.run(debug=True)
