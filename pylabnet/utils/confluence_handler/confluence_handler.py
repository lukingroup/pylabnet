""" Handle the confluence uploading"""
from decouple import config
import datetime
from atlassian import Confluence
from pylabnet.utils.helper_methods import load_config, get_os
import ctypes
import os
from PyQt5 import QtWidgets, uic, QtCore, QtGui
import sys
from functools import partial
import numpy as np
import logging


class Confluence_Handler():
    """ Handle the gui's confluence handler except main window (log server) """

    def __init__(self, parent_wins, app, log_client):
        self.log = log_client
        self.confluence_popup = Confluence_Popping_Windows(parent_wins, app, self.log, "Confluence_info_window")


class LaunchControl_Confluence_Handler():
    """ Handle the main window (log server)'s confluence setting """

    def __init__(self, controller, app):

        self.confluence_popup = LaunchControl_Confluence_Windows(controller, app, 'Confluence_info_from_LaunchControl')


class Confluence_Popping_Windows(QtWidgets.QMainWindow):
    """ Instantiate a popping-up window, which documents the confluence setting, but not show until users press popping-up button.
        It loads html template from 'pylabnet/configs/gui/html_template/html_template_0.html' as the base,
        and append it to the confluence page by setting information.
        self.load determines whether it is in the 'upload' mode. If it is not, then update the info. It it is, then screenshot the whole gui and save into the 'temp/ folder/'.
        The screenshot file is then uploaded to the confluence page and then deleted after all things are settled.

        Param: parent_win - the Window class who calls the confluence handler
        Param: url, username, pw, uerkey, dev_root_id - the information required for using confluenc API (https://pypi.org/project/atlassian-python-api/, https://atlassian-python-api.readthedocs.io/ )
        Param: upload (bool) - whether it is in the upload mode or not
        Param: log - log client
        Param: pix - screenshot stuffs, a class defined by QtWidgets.QMainWindow
        Param: Confluence - a class from atlassian (https://pypi.org/project/atlassian-python-api/, https://atlassian-python-api.readthedocs.io/ )
     """

    def __init__(self, parent_wins, app, log_client=None, template="Confluence_info_window"):
        # handle the case that disables the confluence handler
        self.enable = True

        # param (global)
        try:
            self.parent_wins = parent_wins
            self.url = config('CONFLUENCE_URL')
            self.username = config('CONFLUENCE_USERNAME')
            self.pw = config('CONFLUENCE_PW')
            self.userkey = config('CONFLUENCE_USERKEY')
            self.dev_root_id = config('CONFLUENCE_DEV_root_id')
            self.log = log_client
        except:
            self.log.error("Confluence:.env does not have confluence key! Disable the confluence functions")
            self.enable = False

        # param (condition)
        self.upload = False
        self.pix = None
        self._gui_directory = "gui_templates"
        self.app = app  # Application instance onto which to load the GUI.
        self.auto_info_setting_mode = True # automatically access info from the launch control

        # if self.app is None:
        #     if get_os() == 'Windows':
        #         ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('pylabnet')
        #     self.app = QtWidgets.QApplication(sys.argv)
        #     self.app.setWindowIcon(
        #         QtGui.QIcon(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'devices.ico'))
        #     )

        # Initialize parent class QtWidgets.QDialog
        super(Confluence_Popping_Windows, self).__init__()

        try:
            self.confluence = Confluence(
                url='{}/wiki'.format(self.url), # need to add 'wiki', see https://github.com/atlassian-api/atlassian-python-api/issues/252
                username=self.username,
                password=self.pw)
        except:
            self.confluence = None
            self.enable = False
            self.log.error("Confluence key or password is invalid")

        # load the gui, but not show
        self._load_gui(gui_template=template, run=False)

        # the initial fields' info
        timestamp_day = datetime.datetime.now().strftime('%b %d %Y')
        self.space_key_field.setText('DEV')
        self.space_name_field.setText('API Dev Test Space')
        self.page_field.setText("test-uploading graphs {}".format(timestamp_day))
        self.comment_field.setFontPointSize(12)
        self.upload_space_key = self.space_key_field.text()
        self.upload_space_name = self.space_name_field.text()
        self.upload_page_title = self.page_field.text()
        self.upload_setting = self.setting_field.text()
        self.upload_comment = self.comment_field.toPlainText()

        # Handle button pressing
        self.ok_button.clicked.connect(self.okay_event)
        self.cancel_button.clicked.connect(self.cancel_event)
        self.actionchage_typing_mode.triggered.connect(self.Change_typing_mode)

        # Initialize the checkbox setting
        self.setting_checkbox.setChecked(False)
        self.comment_checkbox.setChecked(True)

        # init the space and page as in the launch control
        self.Update_confluence_info()

        # init the reading settings
        if(self.auto_info_setting_mode):
            self.space_name_field.setReadOnly(True)
            self.space_name_field.setStyleSheet("background-color: gray; color: white")
            self.page_field.setReadOnly(True)
            self.page_field.setStyleSheet("background-color: gray; color: white")

        return

    def Change_typing_mode(self):
        if(self.auto_info_setting_mode):
            self.auto_info_setting_mode = False
            self.actionchage_typing_mode.setText('Change to Auto-typing mode (From launch control')

            self.space_name_field.setReadOnly(False)
            self.space_name_field.setStyleSheet("background-color: black; color: white")
            self.page_field.setReadOnly(False)
            self.page_field.setStyleSheet("background-color: black; color: white")

        else:
            self.auto_info_setting_mode = True
            self.actionchage_typing_mode.setText('Change to Manual-typing mode')

            self.Update_confluence_info()
            self.space_name_field.setReadOnly(True)
            self.space_name_field.setStyleSheet("background-color: gray; color: white")
            self.page_field.setReadOnly(True)
            self.page_field.setStyleSheet("background-color: gray; color: white")
        return

    def Update_confluence_info(self):
        try:
            confluence_config_dict = load_config('confluence_upload')
            lab = confluence_config_dict["lab"]
        except:
            self.log.error("Confluence-cannot find the confluence_upload.json in the config folder!")
            self.enable = False

        if(not self.enable):
            self.log.error("Confluence-Update_confluence_info: has disabled the confluence functions")
            return

        # access metadata
        try:
            metadata = self.log.get_metadata()

            self.upload_space_key = metadata['confluence_space_key_' + lab]
            self.upload_space_name = metadata['confluence_space_name_' + lab]
            self.upload_page_title = metadata['confluence_page_' + lab]
        except:
            self.log.error("Confluence-Update info:cannot load the metadata or does not have confluence key in the metadata")
            self.enable = False

        # update display
        self.space_name_field.setReadOnly(False)
        self.page_field.setReadOnly(False)

        self.space_key_field.setText(self.upload_space_key)
        self.space_name_field.setText(self.upload_space_name)
        self.page_field.setText(self.upload_page_title)

        if(self.auto_info_setting_mode):
            self.space_name_field.setReadOnly(True)
        if(self.auto_info_setting_mode):
            self.page_field.setReadOnly(True)
        return

    def Popup_Update(self):
        self.upload = False
        self.ok_button.setText("OK")
        self.space_key_field.setText(self.upload_space_key)
        self.space_name_field.setText(self.upload_space_name)
        self.page_field.setText(self.upload_page_title)
        self.setting_field.setText(self.upload_setting)
        self.comment_field.setPlainText(self.upload_comment)

        self.ok_button.setText("Ok")
        self.setWindowTitle(self.upload_space_key + '/' + self.upload_page_title)
        self._run_gui()
        self.ok_button.setShortcut("Ctrl+Return")

    def Popup_Upload(self):
        self.upload = True

        #screenshot
        self.pix = self.parent_wins.grab()

        # access the info of the space and page from the launch control
        if(self.auto_info_setting_mode):
            self.Update_confluence_info()

        # display setting
        self.ok_button.setText("Upload")
        self.space_key_field.setText(self.upload_space_key)
        self.space_name_field.setText(self.upload_space_name)
        self.page_field.setText(self.upload_page_title)
        self.setting_field.setText(self.upload_setting)
        self.comment_field.setPlainText(self.upload_comment)

        # pop out
        self._run_gui()
        self.setWindowTitle(self.upload_space_key + '/' + self.upload_page_title)
        self.ok_button.setShortcut("Ctrl+Return")

    def cancel_event(self):
        self.close()

    def okay_event(self):
        self.upload_space_key = self.space_key_field.text()
        self.upload_space_name = self.space_name_field.text()
        self.upload_page_title = self.page_field.text()
        self.upload_setting = self.setting_field.text()
        self.upload_comment = self.comment_field.toPlainText()

        if(self.upload == False):
            self.close()
            return

        # disbaled case
        if(not self.enable):
            self.log.error("Confluence-Uploading event: has disabled the confluence functions, so the uploading function is disbaled")
            self.close()
            return

        # upload case
        wintitle = self.windowTitle()
        self.setWindowTitle('Uploading ...')
        self.log.info("Uploading to the confluence page")

        # save the temperary file
        timestamp_datetime = datetime.datetime.now().strftime("%b_%d_%Y__%H_%M_%S")
        scrn_shot_filename = "Screenshot_{}".format(timestamp_datetime) + ".png"
        os_string = get_os()
        if os_string == 'Windows':
            scrn_shot_AbsPath = os.path.join("..\\..\\temp", scrn_shot_filename)
        elif os_string == "Linux":
            scrn_shot_AbsPath = os.path.join("../../temp", scrn_shot_filename)
        self.pix.save(scrn_shot_AbsPath)

        # upload
        self.upload_pic(scrn_shot_AbsPath, scrn_shot_filename)

        # delete the temperary file
        try:
            os.remove(scrn_shot_AbsPath)
        except:
            self.log.error("cannot remoe the temperary graph.")

        self.setWindowTitle(wintitle)
        self.upload = False

        self.log.info("Finish uploading")
        self.close()
        return

    def _load_gui(self, gui_template=None, run=True):
        """ Loads a GUI template to the main window.

        Currently assumes all templates are in the directory given by the self._gui_directory. If no
        gui_template is passed, the self._default_template is used. By default, this method also runs the GUI window.

        :param gui_template: name of the GUI template to use (str)
        :param run: whether or not to also run the GUI (bool)
        """

        if gui_template is None:
            gui_template = self._default_template

        # Check for proper formatting
        if not gui_template.endswith(".ui"):
            gui_template += ".ui"

        # Find path to GUI
        # Currently assumes all templates are in the directory given by the self._gui_directory attribute

        # self._ui = os.path.join(
        #     os.path.dirname(os.path.abspath(__file__ )),
        #     "..\\..\\",
        #     self._gui_directory,
        #     gui_template
        # )

        os_string = get_os()
        if os_string == 'Windows':
            pyqtpath = os.path.abspath("..\\..\\pylabnet\\gui\\pyqt")
        elif os_string == "Linux":
            pyqtpath = os.path.abspath("../../pylabnet/gui/pyqt")

        self._ui = os.path.join(
            (pyqtpath),
            self._gui_directory,
            gui_template
        )

        # Load UI
        try:
            uic.loadUi(self._ui, self)
        except FileNotFoundError:
            raise

        if run:
            self._run_gui()

    def _run_gui(self):
        """Runs the GUI. Displays the main window"""

        self.show()

    def upload_pic(self, scrn_shot_AbsPath, scrn_shot_filename):
        ''' Upload the picture if the page exists, otherwise firtst create a new page and then upload the picture
        '''
        if(self.confluence.page_exists(self.upload_space_key, self.upload_page_title)):
            upload_page_id = self.confluence.get_page_id(self.upload_space_key, self.upload_page_title)
        else:
            response = self.confluence.update_or_create(
                parent_id=self.dev_root_id,
                title=self.upload_page_title,
                body='',
                representation='storage')

            upload_page_id = response['id']

        self.upload_and_append_picture(
            fileAbsPath=scrn_shot_AbsPath,
            filename=scrn_shot_filename,
            comment=self.upload_comment,
            settings=self.upload_setting,
            page_id=upload_page_id,
            page_title=self.upload_page_title)

        return

    def replace_html(self, base_html, replace_dict):
        '''
        Reads in a HTML template and replaces occurences of the keys of replace_dict by the key values.
        '''
        with open(base_html, "r+") as f:
            replaced_html = f.read()

            for key in replace_dict:
                replaced_html = replaced_html.replace(key, replace_dict[key])
        return replaced_html

    def append_rendered_html(self, base_html, replace_dict, page_id, page_title, silent=True):
        '''
        Renders base_html according to replace_dict and appends it on existing page
        '''

        append_html = self.replace_html(base_html, replace_dict)

        status = self.confluence.append_page(
            page_id=page_id,
            title=page_title,
            append_body=append_html
        )
        self.log.info('PAGE URL: ' + status['_links']['base'] + status['_links']['webui'])

        return status

    def upload_and_append_picture(self, fileAbsPath, filename, comment, settings, page_id, page_title):
        ''' Upload a picture and embed it to page, alongside measurement setting informations and possible comments
        '''
        if(not self.enable):
            return

        self.confluence.attach_file(fileAbsPath, name=None, content_type=None, page_id=page_id, title=None, space=None, comment=None)

        try:
            confluence_config_dict = load_config('confluence_upload')
            templates_root = confluence_config_dict['templates_root']
        except:
            self.log.error("cannot find the confluence_upload.json in the config folder!")
            self.enable = False
            return

        try:
            if(self.setting_checkbox.isChecked() and self.comment_checkbox.isChecked()):
                html_template_filename = confluence_config_dict['html_template_filename']
            elif(self.setting_checkbox.isChecked() and not self.comment_checkbox.isChecked()):
                html_template_filename = confluence_config_dict['html_template_no_comment_filename']
            elif(not self.setting_checkbox.isChecked() and self.comment_checkbox.isChecked()):
                html_template_filename = confluence_config_dict['html_template_no_setting_filename']
            else:
                html_template_filename = confluence_config_dict['html_template_neither_filename']
        except:
            self.enable = False
            self.log.error("Confluence: config file's format is not correct! it requires 4 keys: 'html_template_filename', 'html_template_no_comment_filename', \
                'html_template_no_setting_filename', 'html_template_neither_filename'")
            return

        # base_html = '{}\\{}'.format(templates_root, html_template_filename)

        os_string = get_os()
        if os_string == 'Windows':
            base_html = '{}\\{}'.format(templates_root, html_template_filename)
        elif os_string == "Linux":
            base_html = '{}/{}'.format(templates_root, html_template_filename)

        timestamp_date = datetime.datetime.now().strftime('%Y-%m-%d')
        timestamp_time = datetime.datetime.now().strftime('%H:%M')

        replace_dict = {
            'DATE': timestamp_date,
            'TIME': timestamp_time,
            'USERKEY': self.userkey,
            'SETTING': settings,
            'COMMENT': comment,
            'FILENAME': filename
        }
        # self.log.info(replace_dict)

        status = self.append_rendered_html(base_html, replace_dict, page_id, page_title)

        return status


class LaunchControl_Confluence_Windows(QtWidgets.QMainWindow):
    '''
    It instantiates the confluence window for the main window (Log server). It only shows when users press the button. The updatted info will be saved into
    the new entry of the metadata's dictionary

    Param: controller - the Controller class who calls the confluence handler
    Param: url, username, pw, uerkey, dev_root_id - the information required for using confluenc API (https://pypi.org/project/atlassian-python-api/, https://atlassian-python-api.readthedocs.io/ )
    Param: dict_name_key - the dictionary of space's name -> key
    Param: Confluence - a class from atlassian (https://pypi.org/project/atlassian-python-api/, https://atlassian-python-api.readthedocs.io/ )
    '''

    def __init__(self, controller, app, template='Confluence_info_from_LaunchControl'):
        # Initialize parent class QtWidgets.QDialog
        super(LaunchControl_Confluence_Windows, self).__init__()

        # handle the case that disables LaunchControl_Confluence_Windows
        self.enable = True

        # param (global)
        try:
            self.url = config('CONFLUENCE_URL')
            self.username = config('CONFLUENCE_USERNAME')
            self.pw = config('CONFLUENCE_PW')
            self.userkey = config('CONFLUENCE_USERKEY')
            self.dev_root_id = config('CONFLUENCE_DEV_root_id')
        except:
            self.enable = False
            controller.gui_logger.error("Launcher Confluence: Cannot find the confluence key in the .env! Disable the confluence functions")

        # param
        self.controller = controller
        self.app = app  # Application instance onto which to load the GUI.
        self._gui_directory = "gui_templates"
        self.dict_name_key = {}

        if self.app is None:
            if get_os() == 'Windows':
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('pylabnet')
            self.app = QtWidgets.QApplication(sys.argv)
            self.app.setWindowIcon(
                QtGui.QIcon(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'devices.ico'))
            )

        # confluence
        if(not self.enable):
            self.confluence = None

        try:
            self.confluence = Confluence(
                url='{}/wiki'.format(self.url), # need to add 'wiki', see https://github.com/atlassian-api/atlassian-python-api/issues/252
                username=self.username,
                password=self.pw)
        except:
            self.confluence = None
            self.enable = False
            self.controller.gui_logger.error("Launcher Confluence: Confluence key or password is invalid")

        # load the gui, but not show
        self._load_gui(gui_template=template, run=False)

        # the initial fields' info
        timestamp_day = datetime.datetime.now().strftime('%b %d %Y')

        self.space_key_field.setText('DEV')
        self.space_name_field.setText('API Dev Test Space')
        self.page_field.setText("test-uploading graphs {}".format(timestamp_day))
        self.upload_space_key = self.space_key_field.text()
        self.upload_space_name = self.space_name_field.text()
        self.upload_page_title = self.page_field.text()

        # Handle events
        self.space_name_field.textChanged[str].connect(self.change_space_name_event)
        self.ok_button.setShortcut("Ctrl+Return")
        self.ok_button.clicked.connect(partial(self.okay_event, True))
        self.cancel_button.clicked.connect(self.cancel_event)

        return

    def Popup_Update(self):

        if(not self.controller.staticproxy):
            self.controller.log_service.logger.setLevel(logging.INFO)
        response = self.confluence.get_all_spaces(start=0, limit=500, expand=None)['results']
        if(not self.controller.staticproxy):
            self.controller.log_service.logger.setLevel(logging.DEBUG)

        # update dictionary
        # all_space_key_list = [item["key"] for item in response]
        all_space_name_list = [item["name"] for item in response]
        self.dict_name_key = {}
        for item in response:
            self.dict_name_key[item["name"]] = item['key']

        names = QtWidgets.QCompleter(all_space_name_list)
        self.space_name_field.setCompleter(names)
        self.page_field.setReadOnly(True)
        self.page_field.setStyleSheet("background-color: gray; color: white")
        self.setWindowTitle(self.upload_space_key + '/' + self.upload_page_title)

        self._run_gui()
        return

    def change_space_name_event(self):
        if(not self.enable):
            self.controller.gui_logger.error("Launcher Confluence-change_space_name_event: no space list is available.\
                 has disabled the confluece functions")
            return

        # Detect if valid
        if(self.space_name_field.text() not in self.dict_name_key.keys()):
            return

        # Valid
        self.upload_space_name = self.space_name_field.text()
        self.upload_space_key = self.dict_name_key[self.space_name_field.text()]
        self.space_key_field.setText(self.upload_space_key)
        self.page_field.setStyleSheet("background-color: black; color: white")
        self.page_field.setReadOnly(False)

        # autocomplete for pages
        if(not self.controller.staticproxy):
            self.controller.log_service.logger.setLevel(logging.INFO)
        response = self.confluence.get_all_pages_from_space(self.upload_space_key, start=0, limit=500, status=None, expand=None, content_type='page')
        if(not self.controller.staticproxy):
            self.controller.log_service.logger.setLevel(logging.DEBUG)
        all_page_name_list = [item["title"] for item in response]

        if(self.controller.staticproxy):
            if(len(all_page_name_list) > 20):
                self.controller.gui_logger.info(str(all_page_name_list[0:20])[:-1] + '... ]')
            else:
                self.controller.gui_logger.info(all_page_name_list)

        names = QtWidgets.QCompleter(all_page_name_list)
        self.page_field.setCompleter(names)

    def cancel_event(self):
        self.close()
        return

    def okay_event(self, is_close=True):
        # accidents handling
        try:
            confluence_config_dict = load_config('confluence_upload')
        except:
            self.enable = False
        if(is_close is True):
            self.close()
        if(not self.enable):
            self.controller.gui_logger.error("Launcher Confluence-okay-event: has disabled the confluece functions")
            return

        # update upload setting
        lab = confluence_config_dict["lab"]

        self.upload_space_key = self.space_key_field.text()
        self.upload_space_name = self.space_name_field.text()
        self.upload_page_title = self.page_field.text()

        if(self.controller.staticproxy):
            self.controller.gui_logger.update_metadata(**{'confluence_space_key_' + lab: self.upload_space_key})
            self.controller.gui_logger.update_metadata(**{'confluence_space_name_' + lab: self.upload_space_name})
            self.controller.gui_logger.update_metadata(**{'confluence_page_' + lab: self.upload_page_title})
        else:
            self.controller.log_service.metadata.update(**{'confluence_space_key_' + lab: self.upload_space_key})
            self.controller.log_service.metadata.update(**{'confluence_space_name_' + lab: self.upload_space_name})
            self.controller.log_service.metadata.update(**{'confluence_page_' + lab: self.upload_page_title})

        self.controller.main_window.confluence_space.setText('Space:\n' + self.upload_space_name)
        self.controller.main_window.confluence_page.setText('Page:\n' + self.upload_page_title)
        return

    def _load_gui(self, gui_template=None, run=True):
        """ Loads a GUI template to the main window.

        Currently assumes all templates are in the directory given by the self._gui_directory. If no
        gui_template is passed, the self._default_template is used. By default, this method also runs the GUI window.

        :param gui_template: name of the GUI template to use (str)
        :param run: whether or not to also run the GUI (bool)
        """

        if gui_template is None:
            gui_template = self._default_template

        # Check for proper formatting
        if not gui_template.endswith(".ui"):
            gui_template += ".ui"

        # Find path to GUI
        # Currently assumes all templates are in the directory given by the self._gui_directory attribute

        # self._ui = os.path.join(
        #     os.path.dirname(os.path.abspath(__file__ )),
        #     '_gui_directory',
        #     gui_template
        # )

        os_string = get_os()
        if os_string == 'Windows':
            pyqtpath = os.path.abspath("..\\..\\pylabnet\\gui\\pyqt")
        elif os_string == "Linux":
            pyqtpath = os.path.abspath("../../pylabnet/gui/pyqt")

        self._ui = os.path.join(
            # (os.path.abspath("pylabnet\\gui\\pyqt")),
            (pyqtpath),
            self._gui_directory,
            gui_template
        )

        # Load UI
        try:
            uic.loadUi(self._ui, self)
        except FileNotFoundError:
            raise

        if run:
            self._run_gui()

    def _run_gui(self):
        """Runs the GUI. Displays the main window"""

        self.show()
