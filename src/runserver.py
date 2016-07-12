import os
from angular_flask import app

import sys
import logging.handlers
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("landmark")
main_file = os.path.abspath(sys.modules['__main__'].__file__)
main_directory = os.path.dirname(main_file)
handler = logging.handlers.RotatingFileHandler(
              os.path.join(main_directory,'landmark.log'), maxBytes=10*1024*1024, backupCount=5)
handler.setLevel(logging.INFO)
formatter = logging.Formatter(u'%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def runserver():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    runserver()
