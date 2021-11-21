import sensor
import image
import time
import lcd
import uos
from Maix import GPIO
from fpioa_manager import fm, board_info
import audio
from Maix import I2S


# スピーカー設定
fm.register(board_info.SPK_SD, fm.fpioa.GPIO0)
spk_sd = GPIO(GPIO.GPIO0, GPIO.OUT)
spk_sd.value(1)

fm.register(board_info.SPK_DIN, fm.fpioa.I2S0_OUT_D1)
fm.register(board_info.SPK_BCLK, fm.fpioa.I2S0_SCLK)
fm.register(board_info.SPK_LRCLK, fm.fpioa.I2S0_WS)

wav_dev = I2S(I2S.DEVICE_0)

# LCD設定
lcd.init(freq=15000000)
lcd.rotation(2)

# カメラ設定
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)
clock = time.clock()
sensor.run(1)

# ボタン設定
fm.register(board_info.BUTTON_A, fm.fpioa.GPIO1)
button_a = GPIO(GPIO.GPIO1, GPIO.IN, GPIO.PULL_UP)
fm.register(board_info.BUTTON_B, fm.fpioa.GPIO2)
button_b = GPIO(GPIO.GPIO2, GPIO.IN, GPIO.PULL_UP)

# LEDライト設定
fm.register(board_info.LED_R, fm.fpioa.GPIO0)
led_r = GPIO(GPIO.GPIO0, GPIO.OUT)
fm.register(board_info.LED_G, fm.fpioa.GPIO4)
led_g = GPIO(GPIO.GPIO4, GPIO.OUT)
fm.register(board_info.LED_B, fm.fpioa.GPIO3)
led_b = GPIO(GPIO.GPIO3, GPIO.OUT)
light_on_flag = False
led_r.value(1)
led_g.value(1)
led_b.value(1)

# 写真保存先のディレクトリ設定
dir_sd = "/sd"
dirname_picture = "pictures"

uos.chdir(dir_sd)
dirname_list = uos.listdir()
if dirname_picture not in dirname_list:
    uos.mkdir(dirname_picture)


dir_picture = dir_sd + '/' + dirname_picture

# 状態パラメータ初期化
mode = "camera"  # initial mode
photo_mode_first_time = True  # flag

# その他パラメータ
thresh_long_press_a = 4


def get_picture_filename_list():
    uos.chdir(dir_picture)
    return uos.listdir()


def get_latest_image_filename():
    picture_filename_list = get_picture_filename_list()
    if len(picture_filename_list) == 0:
        return "{0:0=8}.bmp".format(0)
    else:
        return picture_filename_list[-1]


drawing_picture_filename = get_latest_image_filename()


def play_sound(filename, volume=20):
    try:
        player = audio.Audio(path=filename)
        player.volume(volume)
        wav_info = player.play_process(wav_dev)
        wav_dev.channel_config(wav_dev.CHANNEL_1, I2S.TRANSMITTER,
                               resolution=I2S.RESOLUTION_16_BIT,
                               align_mode=I2S.STANDARD_MODE)
        wav_dev.set_sample_rate(wav_info[1])
        while True:
            ret = player.play()
            if ret is None:
                break
            elif ret == 0:
                break
        player.finish()

    except Exception as e:
        print(e)
        lcd.draw_string(lcd.width()//2-100, lcd.height()//2-4,
                        "Error: play_sound", lcd.WHITE, lcd.RED)


def image_path_to_display_filename(path):
    # 表示用に3桁にしたファイル名
    filename_number = int(path.replace(
        dir_picture + '/', '').replace('.bmp', ''))
    return "{0:0=3}.bmp".format(filename_number)


def draw_picture(drawing_picture_path):
    global photo_mode_first_time

    try:
        # 写真読み込み
        img = image.Image()
        img.draw_image(image.Image(
            drawing_picture_path).resize(168, 94), 36, 20)

        # 枠と線を描画
        color = (50, 100, 100)
        thickness = 3
        img.draw_line(0, 0, 35, 19, color, thickness=thickness)
        img.draw_line(239, 134, 204, 114, color, thickness=thickness)
        img.draw_line(239, 0, 204, 19, color, thickness=thickness)
        img.draw_line(0, 134, 35, 114, color, thickness=thickness)
        img.draw_rectangle(35, 19, 168, 94, color, thickness=thickness)

        lcd.display(img)

        # 写真ファイル名表示
        lcd.draw_string(95, 115, image_path_to_display_filename(
            drawing_picture_path), lcd.WHITE, lcd.BLACK)

        # ボタン説明表示（初回のみ）
        if photo_mode_first_time is True:
            photo_mode_first_time = False
            lcd.draw_string(100, 3, '^', lcd.WHITE, lcd.BLACK)
            lcd.draw_string(100, 8, 'camera mode', lcd.WHITE, lcd.BLACK)
            lcd.draw_string(195, 60, '    >', lcd.WHITE, lcd.BLACK)
            lcd.draw_string(195, 75, ' next', lcd.WHITE, lcd.BLACK)
            lcd.draw_string(195, 90, 'photo', lcd.WHITE, lcd.BLACK)

        return drawing_picture_path

    except Exception as e:
        print(e)
        lcd.draw_string(lcd.width()//2-100, lcd.height()//2-4,
                        "Error: draw_picture", lcd.WHITE, lcd.RED)


def turn_on_light(light_on_flag):
    print("light on")
    light_on_flag = True
    led_r.value(not light_on_flag)
    led_g.value(not light_on_flag)
    led_b.value(not light_on_flag)
    return light_on_flag


def turn_off_light(light_on_flag):
    print("light off")
    light_on_flag = False
    led_r.value(not light_on_flag)
    led_g.value(not light_on_flag)
    led_b.value(not light_on_flag)
    return light_on_flag


def draw_string_count_a(count_a, mode):
    if mode == "camera":
        lcd.draw_string(148 - 30 * (count_a-1), 115, '  .  ',
                        lcd.WHITE, lcd.BLACK)
    else:
        # 進む/戻る矢印
        lcd.draw_string(70, 115, '<-', lcd.WHITE, lcd.BLACK)
        lcd.draw_string(160, 115, '->', lcd.WHITE, lcd.BLACK)
        lcd.draw_string(148 - 30 * (count_a-1), 100, '  .  ',
                        lcd.WHITE, lcd.BLACK)


def sort_listdir(list):
    # ".bmp"の部分を削除
    list = [i.replace(".bmp", "") for i in list]

    # ソート
    list = sorted(list, key=int)

    # ".bmp"を付加
    list = [i + ".bmp" for i in list]

    return list


def get_save_path():
    latest_image_filename = get_latest_image_filename()
    new_image_number = int(latest_image_filename.replace('.bmp', '')) + 1
    return dir_picture + '/'+"{0:0=8}.bmp".format(new_image_number)


def save_image():
    path = get_save_path()

    # 下で写真ファイル名の右側に空白表示するので左右のバランスをとるために左側にも表示する
    lcd.draw_string(55, 115, '     ', lcd.WHITE, lcd.BLACK)
    # 写真ファイル名表示
    lcd.draw_string(95, 115, image_path_to_display_filename(path),
                    lcd.WHITE, lcd.BLACK)
    # "."の表示が残らないように空白を表示する
    lcd.draw_string(160, 115, '   ', lcd.WHITE, lcd.BLACK)

    print("saving path:", path)
    try:
        img.save(path)
    except Exception as e:
        print(e)
        lcd.draw_string(lcd.width()//2-100, lcd.height()//2-4,
                        "Error: save_image", lcd.WHITE, lcd.RED)
    time.sleep(1)


def long_press_a(mode, light_on_flag, drawing_picture_filename):
    print("long_press_a")
    if mode == "camera":
        # ライト点灯状態だと音がならないようなので、ライト消灯状態で音を鳴らす
        if light_on_flag is True:
            light_on_flag = turn_off_light(light_on_flag)
            show_image('/sd/image/light_off.jpg')
            play_sound("/sd/sound/light_off.wav", 40)
            time.sleep(1)
        else:
            show_image('/sd/image/light_on.jpg')
            play_sound("/sd/sound/light_on.wav", 40)
            light_on_flag = turn_on_light(light_on_flag)
            time.sleep(1)

    else:  # mode == "photo"
        # 次の動作予告として戻るのみを表示するために、進むの表示を削除
        lcd.draw_string(160, 115, '  ', lcd.WHITE, lcd.BLACK)

        image_filenames = uos.listdir()
        image_filenames = sort_listdir(image_filenames)
        index = image_filenames.index(drawing_picture_filename)
        index_inc = (index-1)
        drawing_picture_filename = image_filenames[index_inc]
        draw_picture(dir_picture + '/' + drawing_picture_filename)
        play_sound("/sd/sound/mae_high.wav", 40)
    return light_on_flag, drawing_picture_filename


def short_press_a(mode, drawing_picture_filename):
    print("short_press_a")
    if mode == "camera":
        play_sound("/sd/sound/shutter.wav", 40)
        save_image()
    else:  # mode == "photo"
        # 次の動作予告として進むのみを表示するために、戻るの表示を削除
        lcd.draw_string(70, 115, '  ', lcd.WHITE, lcd.BLACK)

        image_filenames = uos.listdir()
        image_filenames = sort_listdir(image_filenames)
        index = image_filenames.index(drawing_picture_filename)
        if (index + 1) < len(image_filenames):
            index_inc = (index+1)
        else:
            index_inc = (index+1) - len(image_filenames)
        drawing_picture_filename = image_filenames[index_inc]
        draw_picture(dir_picture + '/' + drawing_picture_filename)
        play_sound("/sd/sound/tsugi_high.wav", 40)
    return drawing_picture_filename


def show_image(path):
    # startup image
    try:
        img = image.Image(path)
        img = img.resize(240, 135)       # Resize the image
        lcd.display(img)
    except Exception as e:
        print(e)
        lcd.draw_string(lcd.width()//2-100, lcd.height()//2-4,
                        "Error: show_image", lcd.WHITE, lcd.RED)


# main start
show_image("/sd/image/startup.jpg")
play_sound("/sd/sound/kame_camera_sound.wav", 40)
play_sound("/sd/voice/kame_camera.wav", 20)
time.sleep(2)

while(True):
    if mode == "camera":
        img = sensor.snapshot()         # Take a picture and return the image.
        img = img.copy((0, 12, 180, 101))
        img = img.resize(240, 135)       # Resize the image
        lcd.display(img)                # Display on LCD

    # B button
    if button_b.value() == 0:
        if mode == "camera":
            mode = "photo"
            print("camera to photo")
            show_image('/sd/image/photo_mode.jpg')
            play_sound("/sd/sound/shashin.wav", 40)
            drawing_picture_filename = draw_picture(
                get_latest_image_filename())

        else:
            mode = "camera"
            print("photo to camera")
            show_image('/sd/image/camera_mode.jpg')
            play_sound("/sd/sound/camera.wav", 40)
        time.sleep(1)

    # A button
    if button_a.value() == 0:
        count_a = 0
        while True:
            time.sleep(0.2)
            count_a += 1
            print(count_a)
            draw_string_count_a(count_a, mode)

            # long press
            if count_a >= thresh_long_press_a:
                light_on_flag, drawing_picture_filename = long_press_a(
                    mode, light_on_flag, drawing_picture_filename)
                break

            if button_a.value() == 1:
                # short press
                if count_a <= thresh_long_press_a:
                    drawing_picture_filename = short_press_a(
                        mode, drawing_picture_filename)
                    break

                else:
                    # long press
                    continue
