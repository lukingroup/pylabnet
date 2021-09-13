from decouple import config
import datetime
from atlassian import Confluence
from pylabnet.utils.helper_methods import load_config, get_os, load_script_config, get_config_filepath
import ctypes
import os 
from PyQt5 import QtWidgets, uic, QtCore, QtGui
import sys

class Confluence_Handler(QtWidgets.QDialog):
    def __init__(self, app, template):
        # params
        self.url = config('CONFLUENCE_URL')
        self.username = config('CONFLUENCE_USERNAME')
        self.pw = config('CONFLUENCE_PW')
        self.userkey = config('CONFLUENCE_USERKEY')
        self.dev_root_id = config('CONFLUENCE_DEV_root_id')

        self._gui_directory = "gui_templates"
        self.app = app  # Application instance onto which to load the GUI.
        
        if self.app is None:
            if get_os() == 'Windows':
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('pylabnet')
            self.app = QtWidgets.QApplication(sys.argv)
            self.app.setWindowIcon(
                QtGui.QIcon(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'devices.ico'))
            )

        # Initialize parent class QWidgets.QMainWindow
        super(Confluence_Handler, self).__init__()


        self.confluence = Confluence(
            url='{}/wiki'.format(self.url), # need to add 'wiki', see https://github.com/atlassian-api/atlassian-python-api/issues/252
            username=self.username,
            password=self.pw)

        # load the gui, but not show
        self._load_gui(gui_template="Confluence_info_setting", run=False)

        # the initial fields' info
        timestamp_date = datetime.datetime.now().strftime('%b %d %Y')
        timestamp_day = datetime.datetime.now().strftime('%b %d %Y')
        self.space_field.setText('DEV')
        self.page_field.setText("test-uploading graphs {}".format(timestamp_day) )
        self.upload_space = self.space_field.text()
        self.upload_page_title = self.page_field.text()
        

        # accept and reject button
        self.buttonBox.accepted.connect(self.myaccept)
        self.buttonBox.rejected.connect(self.myreject)

        return

    def Popup(self):
        self._run_gui()
        self.setWindowTitle( self.upload_space + '/' + self.upload_page_title )
    
    def myreject(self):
        self.close()
        

    def myaccept(self):
        self.upload_space = self.space_field.text()
        self.upload_page_title = self.page_field.text()
        self.close()


    def _load_gui(self, gui_template=None, run=True):
        """ Loads a GUI template to the main window.

        Currently assumes all templates are in the directory given by the self._gui_directory attribute. If no
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

    def upload_pic(self, scrn_shot_AbsPath, scrn_shot_filename, upload_comment, upload_setting):
        ''' Upload the picture if the page exists, otherwise firtst create a new page and then upload the picture
        '''
        if( self.confluence.page_exists(self.upload_space, self.upload_page_title) ):
            upload_page_id = self.confluence.get_page_id(self.upload_space, self.upload_page_title)
        else:
            response = self.confluence.update_or_create(
                parent_id= self.dev_root_id, 
                title = self.upload_page_title,
                body='',
                representation='storage')

            upload_page_id = response['id']
            web_url = response['_links']['base']+response['_links']['webui']
            print(web_url)

        self.upload_and_append_picture(
            fileAbsPath=scrn_shot_AbsPath,
            filename=scrn_shot_filename, 
            comment=upload_comment, 
            settings=upload_setting, 
            page_id=upload_page_id, 
            page_title=self.upload_page_title)



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

        timestamp =  datetime.datetime.now().strftime('%Y-%m-%d')

        replace_dict = {
        'DATETIME' : timestamp,
        'USERKEY'  : self.userkey,
        'SETTING'  : settings,
        'COMMENT'  : comment,
        'FILENAME' : filename
        }

        status = self.append_rendered_html( base_html, replace_dict, page_id, page_title)

        return status


        
