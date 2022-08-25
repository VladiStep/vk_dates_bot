from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, MoveTargetOutOfBoundsException, WebDriverException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains

import os, shutil, sys, traceback, logging
from pathlib import Path
from time import sleep, time
from datetime import datetime, timedelta
from random import randint
from typing import Union


# (все задержки измеряются в секундах)

# Имя профиля ('Default' - по умолчанию)
profile_name = 'Default'
# Время ожидания загрузки элементов
timeout_sec = 10
# Порог роста, при достижении которого нужно ставить дизлайк
height_threshold = 180
# Диапазон времени задержки между лайками
delay_short = [2, 5]
# Диапазон времени задержки после достижения лимита
delay_premium = [15000, 16000]


#region Вспомогательные функции
def copy_directory(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            try:
                shutil.copytree(s, d, symlinks, ignore)
            except:
                continue
        else:
            try:
                shutil.copy2(s, d)
            except:
                continue

def copy_profile_dir(src, dst):
    if os.path.exists(dst):
        if time() - os.path.getctime(dst) >= 3600:
            logging.info('Удаление существующей копии профилей...')
            shutil.rmtree(dst)
        else:
            logging.info('Копия профилей создана менее часа назад, копирование отменено.')
            return
    
    try:
        logging.info('Копирование папки профилей...')
        copy_directory(src, dst)
        logging.info('Копирование завершено.')
    except:
        logging.error('Не удается скопировать папку с профилями, проверьте путь к директории и попробуйте снова.')
        input('Нажмите Enter для выхода.')
        sys.exit()

def find_element(root, by, value) -> Union[WebElement,bool]:
    try:
        return root.find_element(by, value)
    except NoSuchElementException:
        return False

def click(elem):
    try:
        ActionChains(driver).move_to_element(elem).click().perform()
        return True
    except MoveTargetOutOfBoundsException:
        driver.execute_script('arguments[0].scrollIntoView();', elem)
        try:
            ActionChains(driver).move_to_element(elem).click().perform()
        except MoveTargetOutOfBoundsException:
            error_refresh('Не удалось нажать лайк/дизлайк - увеличьте размер окна, чтобы кнопки "лайк" и "дизлайк" были видны без прокрутки вниз.')
            sleep(5)
            return False


def error_refresh(msg, newline=False):
    global cont

    sep = ' '
    if newline:
        sep = '\n'
    
    logging.error(f'{msg}{sep}Перезагрузка страницы...')
    cont = None
    driver.refresh()
    sleep(1)

def error_exit(msg):
    logging.error(msg)
    input('Нажмите Enter для выхода.')
    driver.close()
    sys.exit()

def get_delay(is_premium):
    if is_premium:
        return randint(delay_premium[0], delay_premium[1])
    else:
        return randint(delay_short[0], delay_short[1])

def sleep_random(is_premium):
    delay = get_delay(is_premium)

    if is_premium:
        new_date = datetime.now() + timedelta(seconds=delay)
        new_date = new_date.strftime('%d.%m.%y %H:%M:%S')
        logging.info(f'Задержка после достижения лимита - {delay} с. Время продолжения работы - {new_date}.')
    else:
        logging.info(f'Задержка перед следующим лайком - {delay} с.')
    
    sleep(delay)
#endregion


logging.basicConfig(format='[%(levelname)s] - [%(asctime)s] -  %(message)s', datefmt='%d.%m.%y %H:%M:%S',
                    level=logging.INFO)


chrome_profiles_path = fr'C:\Users\{os.getlogin()}\AppData\Local\Google\Chrome\User Data'
script_dir_path = Path(__file__).parent.resolve()
data_dir_path = f'{script_dir_path}\data' 

# Копирование профилей
copy_profile_dir(chrome_profiles_path, data_dir_path)

#region Запуск браузера
options = webdriver.ChromeOptions() 
options.add_experimental_option('excludeSwitches', ['enable-logging'])
options.add_argument('--log-level=3')
options.add_argument(f'user-data-dir={data_dir_path}')
options.add_argument(f'--profile-directory={profile_name}')
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
timeout = WebDriverWait(driver, timeout_sec)
#endregion

driver.get('https://vk.com/dating')
cont = None

while True:
    try:
        #region Проверка доступности приложения
        if cont is None:
            try:
                cont = timeout.until(EC.presence_of_element_located((By.CLASS_NAME, 'app_container')))
            except TimeoutException:
                error_exit('Не выполнен вход в ВК или в приложение (или превышено время ожидания).')

            sleep(2)

            iframe = find_element(cont, By.TAG_NAME, 'iframe')
            if not iframe:
                error_refresh('Не удалось найти iframe приложения.')
                continue
            driver.switch_to.frame(iframe)
        #endregion

        #region Нахождение кнопок "лайк" и "дизлайк"
        # Нахождение личной информации (+ ожидание загрузки профиля)
        tags_cont = None
        try:
            # Если отобразилась табличка премиума, "tags_cont" будет содержать её заместо личной информации
            tags_cont = timeout.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '.TagList, #view_get_premium')))
        except TimeoutException:
            error_refresh('Не удалось найти список личных данных (или превышено время ожидания).')
            continue
        
        # Если "tags_cont" содержит табличку премиума
        if tags_cont.get_attribute('id') == 'view_get_premium':
            logging.info('Лимит достигнут.')
            sleep_random(True)
            logging.info('Перезагрузка страницы...')
            cont = None
            driver.refresh()
            sleep(1)
            continue

        buttons_cont = find_element(driver, By.CLASS_NAME, 'CardBioReactions')
        if not buttons_cont:
            error_refresh('Не удалось найти контейнер кнопок "лайк" и "дизлайк".')
            continue

        like_button = find_element(buttons_cont, By.CLASS_NAME, 'ReactionButton--reaction-like')
        dislike_button = find_element(buttons_cont, By.CLASS_NAME, 'ReactionButton--reaction-dislike')
        if not like_button:
            error_refresh('Не найдена кнопка "лайк".')
            continue
        if not dislike_button:
            error_refresh('Не найдена кнопка "дизлайк".')
            continue
        #endregion

        #region Нахождение роста
        height = -1
        tags = tags_cont.find_elements(By.TAG_NAME, 'div')
            
        for tag in tags:
            tag_img = find_element(tag, By.TAG_NAME, 'img')
            if 'height' in tag_img.get_attribute('src'):
                height = int(tag.get_attribute('innerText').split(' ')[0])
                break

        # Проверка роста
        if height == -1:
            logging.warning('Рост не найден - лайк.')
            if not click(like_button):
                continue
        else:
            if height < height_threshold:
                logging.info(f'Рост - {height} - лайк.')
                if not click(like_button):
                    continue
            else:
                logging.info(f'Рост - {height} - дизлайк.')
                if not click(dislike_button):
                    continue
        #endregion
        
        sleep_random(False)
        
    except WebDriverException:
        logging.error('Работа программы прекращена.')
        input('Нажмите Enter для выхода.')
        sys.exit()
    except Exception:
        error_refresh(f'Произошла ошибка.\n{traceback.format_exc()}', True)