from decouple import config
import datetime
from atlassian import Confluence
from pylabnet.utils.helper_methods import load_config, get_os, load_script_config, get_config_filepath
import ctypes
import os 
from PyQt5 import QtWidgets, uic, QtCore, QtGui
import sys
from functools import partial
import numpy as np
import logging

class Confluence_Handler():
    def __init__(self,  parent_wins, app,  log_client):
        self.log = log_client
        self.confleunce_popup = Confluence_Popping_Windows(parent_wins, app, self.log, "Confluence_info_window" )
        
        # needs to be inplemented on launch_control.py
        # c_params = log_client.get_confluence_parameters()


class LaunchControl_Confluence_Handler():
    def __init__(self,  controller, app):
        self.confleunce_popup = LaunchControl_Confluence_Windows(controller, app, 'Confluence_info_from_LaunchControl' )


class Confluence_Popping_Windows(QtWidgets.QMainWindow):
    def __init__(self, parent_wins, app, log_client=None, template= "Confluence_info_window"):
        # param (global)
        self.parent_wins = parent_wins
        self.url = config('CONFLUENCE_URL')
        self.username = config('CONFLUENCE_USERNAME')
        self.pw = config('CONFLUENCE_PW')
        self.userkey = config('CONFLUENCE_USERKEY')
        self.dev_root_id = config('CONFLUENCE_DEV_root_id')
        self.log = log_client

        # param (condition)
        self.upload = False
        self.pix = None
        self._gui_directory = "gui_templates"
        self.app = app  # Application instance onto which to load the GUI.
        
        if self.app is None:
            if get_os() == 'Windows':
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('pylabnet')
            self.app = QtWidgets.QApplication(sys.argv)
            self.app.setWindowIcon(
                QtGui.QIcon(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'devices.ico'))
            )

        # Initialize parent class QtWidgets.QDialog
        super(Confluence_Popping_Windows, self).__init__()

        self.confluence = Confluence(
            url='{}/wiki'.format(self.url), # need to add 'wiki', see https://github.com/atlassian-api/atlassian-python-api/issues/252
            username=self.username,
            password=self.pw)
            
            

        # load the gui, but not show
        self._load_gui(gui_template=template, run=False)
        

        # the initial fields' info
        timestamp_date = datetime.datetime.now().strftime('%b %d %Y')
        timestamp_day = datetime.datetime.now().strftime('%b %d %Y')
        self.space_key_field.setText('DEV')
        self.space_name_field.setText('API Dev Test Space')
        self.page_field.setText("test-uploading graphs {}".format(timestamp_day) )
        self.upload_space_key = self.space_key_field.text()
        self.upload_space_name = self.space_name_field.text()
        self.upload_page_title = self.page_field.text()
        self.upload_setting = self.setting_field.text()
        self.upload_comment = self.comment_field.text()

        # Handle button pressing
        self.ok_button.clicked.connect(self.okay_event)
        self.cancel_button.clicked.connect(self.cancel_event)
        self.actionaccess_from_logserver.triggered.connect(self.Update_confluence_info)

        # init the space and page as in the launch control
        self.Update_confluence_info()
        return

    def Update_confluence_info(self):
        # access metadata
        metadata = self.log.get_metadata()
        self.upload_space_key = metadata['confluence_space_key']
        self.upload_space_name = metadata['confluence_space_name']
        self.upload_page_title = metadata['confluence_page']
        
        # update display
        self.space_key_field.setText(self.upload_space_key)
        self.space_name_field.setText(self.upload_space_name)
        self.page_field.setText(self.upload_page_title)
        return
        

    def Popup_Update(self):
        self.ok_button.setText("OK")
        self.space_key_field.setText(self.upload_space_key)
        self.space_name_field.setText(self.upload_space_name)
        self.page_field.setText(self.upload_page_title)
        self.setting_field.setText(self.upload_setting)
        self.comment_field.setText(self.upload_comment)

        self.ok_button.setText("Ok")
        self.setWindowTitle( self.upload_space_key + '/' + self.upload_page_title )
        self._run_gui()

    def Popup_Upload(self):
        self.upload = True

        #screenshot
        self.pix = self.parent_wins.grab()

        # display setting
        self.ok_button.setText("Upload")
        self.space_key_field.setText(self.upload_space_key)
        self.space_name_field.setText(self.upload_space_name)
        self.page_field.setText(self.upload_page_title)
        self.setting_field.setText(self.upload_setting)
        self.comment_field.setText(self.upload_comment)

        # pop out
        self._run_gui()
        self.setWindowTitle( self.upload_space_key + '/' + self.upload_page_title )
    
    def cancel_event(self):
        self.close()

    def okay_event(self):
        self.upload_space_key = self.space_key_field.text()
        self.upload_space_name = self.space_name_field.text()
        self.upload_page_title = self.page_field.text()
        self.upload_setting = self.setting_field.text()
        self.upload_comment = self.comment_field.text()
        
        if(self.upload == False):
            self.close()
            return

        # upload case
        wintitle = self.windowTitle()
        self.setWindowTitle('Uploading ...')
        self.log.info("Uploading to the confluence page")

        # save the temperary file
        timestamp_datetime = datetime.datetime.now().strftime("%b_%d_%Y__%H_%M_%S")
        scrn_shot_filename = "Screenshot_{}".format(timestamp_datetime) +  ".png"
        scrn_shot_AbsPath = os.path.join("..\\..\\temp", scrn_shot_filename)
        self.pix.save(scrn_shot_AbsPath)

        # upload
        self.upload_pic(scrn_shot_AbsPath, scrn_shot_filename)

        # delete the temperary file
        os.remove(scrn_shot_AbsPath)

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
        self._ui = os.path.join(
            (os.path.abspath("..\\..\\pylabnet\\gui\\pyqt" ) ),
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
        if( self.confluence.page_exists(self.upload_space_key, self.upload_page_title) ):
            upload_page_id = self.confluence.get_page_id(self.upload_space_key, self.upload_page_title)
        else:
            response = self.confluence.update_or_create(
                parent_id= self.dev_root_id, 
                title = self.upload_page_title,
                body='',
                representation='storage')

            upload_page_id = response['id']
            web_url = response['_links']['base']+response['_links']['webui']

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

        return status
        
    def upload_and_append_picture(self, fileAbsPath, filename, comment, settings, page_id, page_title):

        ''' Upload a picture and embed it to page, alongside measurement setting informations and possible comments
        '''

        self.confluence.attach_file(fileAbsPath, name=None, content_type=None, page_id=page_id, title=None, space=None, comment=None)

        confluence_config_dict = load_config('confluence_upload')
        templates_root = confluence_config_dict['templates_root']
        html_template_filename = confluence_config_dict['html_template_filename']

        base_html = '{}\\{}'.format(templates_root, html_template_filename)

        timestamp_date =  datetime.datetime.now().strftime('%Y-%m-%d')
        timestamp_time =  datetime.datetime.now().strftime('%H:%M')
        
        replace_dict = {
        'DATE' : timestamp_date,
        'TIME' : timestamp_time,
        'USERKEY'  : self.userkey,
        'SETTING'  : settings,
        'COMMENT'  : comment,
        'FILENAME' : filename
        }
        # self.log.info(replace_dict)

        status = self.append_rendered_html( base_html, replace_dict, page_id, page_title)

        return status



class LaunchControl_Confluence_Windows(QtWidgets.QMainWindow):
    def __init__(self,  controller, app,  template= 'Confluence_info_from_LaunchControl'):
        # param (global)
        self.url = config('CONFLUENCE_URL')
        self.username = config('CONFLUENCE_USERNAME')
        self.pw = config('CONFLUENCE_PW')
        self.userkey = config('CONFLUENCE_USERKEY')
        self.dev_root_id = config('CONFLUENCE_DEV_root_id')
        
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

        # Initialize parent class QtWidgets.QDialog
        super(LaunchControl_Confluence_Windows, self).__init__()
        
        # confluence
        self.confluence = Confluence(
            url='{}/wiki'.format(self.url), # need to add 'wiki', see https://github.com/atlassian-api/atlassian-python-api/issues/252
            username=self.username,
            password=self.pw)

        # load the gui, but not show
        self._load_gui(gui_template=template, run=False)

        # the initial fields' info
        timestamp_day = datetime.datetime.now().strftime('%b %d %Y')
        self.space_key_field.setText('DEV')
        self.space_name_field.setText('API Dev Test Space')
        self.page_field.setText("test-uploading graphs {}".format(timestamp_day) )
        self.upload_space_key = self.space_key_field.text()
        self.upload_space_name = self.space_name_field.text()
        self.upload_page_title = self.page_field.text()

        # Handle events
        self.space_name_field.textChanged[str].connect(self.change_space_name_event)
        self.ok_button.clicked.connect(partial(self.okay_event, True))
        self.cancel_button.clicked.connect(self.cancel_event)

        return


    def Popup_Update(self):
        self.controller.log_service.logger.setLevel(logging.INFO)
        response = self.confluence.get_all_spaces(start=0, limit=500, expand=None)['results']
        self.controller.log_service.logger.setLevel(logging.DEBUG)

        # update dictionary
        all_space_key_list = [item["key"] for item in response]
        all_space_name_list = [item["name"] for item in response]
        self.dict_name_key = { }
        for item in response:
            self.dict_name_key[item["name"]] = item['key']
        

        names = QtWidgets.QCompleter(all_space_name_list)
        self.space_name_field.setCompleter( names )
        self.page_field.setReadOnly(True)
        self.page_field.setStyleSheet("background-color: gray; color: white")
        self.setWindowTitle( self.upload_space_key + '/' + self.upload_page_title )

        self._run_gui()
        return
        
    def change_space_name_event(self):
        # Detect if valid
        if(self.space_name_field.text() not in self.dict_name_key.keys() ):
            return

        # Valid
        self.upload_space_name = self.space_name_field.text()
        self.upload_space_key = self.dict_name_key[self.space_name_field.text()]
        self.space_key_field.setText(self.upload_space_key)
        self.page_field.setStyleSheet("background-color: black; color: white")
        self.page_field.setReadOnly(False)

        # autocomplete for pages
        self.controller.log_service.logger.setLevel(logging.INFO)
        response = self.confluence.get_all_pages_from_space(self.upload_space_key, start=0, limit=100, status=None, expand=None, content_type='page')
        self.controller.log_service.logger.setLevel(logging.DEBUG)
        all_page_name_list = [item["title"] for item in response]
        # self.controller.log_service.logger.info(all_page_name_list)
        names = QtWidgets.QCompleter(all_page_name_list)
        self.page_field.setCompleter( names )

    def cancel_event(self):
        self.close()
        return
        

    def okay_event(self, is_close=True):
        self.upload_space_key = self.space_key_field.text()
        self.upload_space_name = self.space_name_field.text()
        self.upload_page_title = self.page_field.text()
        self.controller.log_service.metadata.update(confluence_space_key =  self.upload_space_key ) 
        self.controller.log_service.metadata.update(confluence_space_name =  self.upload_space_name )
        self.controller.log_service.metadata.update(confluence_page =  self.upload_page_title )
        self.controller.main_window.confluence_space.setText('Space:\n' + self.upload_space_name)
        self.controller.main_window.confluence_page.setText('Page:\n' + self.upload_page_title)
        if(is_close is True): self.close()
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
        
        self._ui = os.path.join(
            (os.path.abspath("..\\..\\pylabnet\\gui\\pyqt" ) ),
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
        