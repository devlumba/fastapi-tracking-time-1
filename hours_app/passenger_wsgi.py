# это показательная версия. Для корректной работы приложения необходимо заменить u0000000 и websitename.ru на ваши.

import sys
import os

INTERP = "/var/www/u0000000/data/www/websitename.ru/venv/bin/python"
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

sys.path.append('/var/www/u0000000/data/www/websitename.ru')

from hours_app.main import application
