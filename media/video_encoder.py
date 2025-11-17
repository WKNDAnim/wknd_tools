"""Video encoding utilities using ffmpeg"""
import subprocess
import os
import tempfile
import re
import glob


def images_to_video(source, output_path, source_type = 'playblast'):
    """
    Convert image sequence to video using ffmpeg
    
    Args:
        image_sequence_pattern (str): Path pattern (e.g., "/path/frame.%04d.png" or list of files)
        output_path (str): Output video path
        
    Returns:
        bool: Success
    """
    if source_type=='playblast':
        return _image_sequence_to_video(source, output_path)
    elif source_type=='folder':
        return _images_list_to_video(source, output_path)


def _image_sequence_to_video(pattern, output_path):

    # 1. Detectar el primer frame de la secuencia
    # Convertir pattern de FFmpeg a glob: "path.%04d.png" → "path.*.png"
    glob_pattern = re.sub(r'%\d*d', '*', pattern)
    matching_files = sorted(glob.glob(glob_pattern))
    
    if not matching_files:
        print(f"❌ No se encontraron archivos con pattern: {glob_pattern}")
        return False
    
    # Extraer número del primer archivo
    first_file = matching_files[0]
    filename = os.path.basename(first_file)
    
    # Buscar números en el nombre del archivo
    numbers = re.findall(r'\d+', filename)
    
    if not numbers:
        print(f"❌ No se encontró número de frame en: {filename}")
        return False
    
    # El último número suele ser el frame number
    start_frame = int(numbers[-1])
    
    print(f"✓ Detectado start frame: {start_frame}")
    print(f"✓ Total frames: {len(matching_files)}")

    vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2," \
    "drawtext=text='Frame %{n}':fontcolor=white:x=w-tw-10:y=10"

    """Convert numbered sequence to video"""
    cmd = [
        'ffmpeg',
        '-y',
        '-start_number',str(start_frame),
        '-framerate', '24',
        '-i', pattern,
        '-c:v', 'libx264',
        '-crf', '18',
        '-preset', 'slow',
        '-pix_fmt', 'yuv420p',
        '-vf', vf,
        output_path
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr.decode()}")
        return False
    
def _images_list_to_video(image_folder, output_path):
    """Convert list of images to video using concat"""
    # Create concat file

    image_paths = list()
    image_files = os.listdir(image_folder)
    valid_extensions = ['.exr', '.png', '.jpg']
    for img in image_files:
        if img.lower().endswith(tuple(valid_extensions)):
            image_paths.append(os.path.join(image_folder, img))
     
    temp_dir = os.path.realpath(tempfile.gettempdir())
    concat_file = os.path.join(temp_dir, "ffmpeg_concat.txt")
    
    try:
        with open(concat_file, 'w') as f:
            for img in image_paths:
                print (img)
                f.write(f"file '{img}'\n")
                f.write(f"duration {1.0/24}\n")
            f.write(f"file '{image_paths[-1]}'\n")  # Last frame
        
        cmd = [
            'ffmpeg',
            '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c:v', 'mjpeg',  # Cambiar a MJPEG como RV
            '-q:v', '2',  # Calidad para MJPEG (1-31, menor es mejor)
            '-pix_fmt', 'yuvj420p',  # Full range JPEG
            '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
            '-color_range', 'jpeg',  # Full range
            '-colorspace', 'bt470bg',  # Rec601 (bt470bg es equivalente)
            '-color_primaries', 'bt470bg',
            '-color_trc', 'bt709',
            output_path
        ]

        subprocess.run(cmd, check=True, capture_output=True)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr.decode()}")
        return False
    finally:
        if os.path.exists(concat_file):
            try:
                os.remove(concat_file)
            except:
                pass