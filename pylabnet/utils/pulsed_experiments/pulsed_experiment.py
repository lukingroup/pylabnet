
import os 
from pylabnet.hardware.awg.zi_hdawg import Driver, Sequence, AWGModule


class PulsedExperiment():


    def get_templates(self, template_directory="sequence_templates"):
      

        # Get all relevant files template files
        current_directory = os.path.dirname(os.path.realpath(__file__))

        template_directory = os.path.join(current_directory, template_directory)

        files = [file for file in os.listdir(template_directory) 
            if  '.seqct' in file and '__init__.py' not in file 
        ]

        files_trimmed = [filename.replace('.seqct', '') for filename in files]

        return files_trimmed

    def replace_placeholders(self):
        """Replaces all sequence placeholders with values"""
        placeholder_dict

                
        # Create Sequence Object and replace placeholder
        placeholder_dict = {
            "c1" : AWG_N
        }

        # Create Sequence Object and replace placeholder
        seq = Sequence(
            hdawg_driver = self.hd,
            sequence = sequence_txt,
            placeholder_dict=placeholder_dict
        )

    def replace_dio_commands(self):
        pass


    def prepare_sequence(self):
        """Prepares sequence"""

        self.replace_placeholders()
        self.replace_dio_commands()





    

    def __init__(self, pulseblocks, assignment_dict, placeholder_dict=None, hd=None, 
    use_template=True, template_name='base_dig_pulse', sequence_string=None, dio_seq_identifier='dig_sequence', template_directory="sequence_templates"):
        """ Initilizes pulseblock experiment

        :hd: Instance of ZI AWG Driver
        :pulseblock_objects: Single Pulseblock object or list of Pulseblock
                    objects.
        :placeholder_dict: Dictionary containing placeholder names and values for the .seqt file.
        :assignment_dict: Assigning channels to DIO output bins.
        :use_template: (bool) If True, look for .seqc template, if false, use
            sequence_string 
        :template_name: (str) Name of the .seqc template file (must be stored in sequence_template_folders)
        :sequence_string: (str) .seqc sequence if no template sequence is used.
        :dio_seq_identifier: (str) Placeholder within .seqct files to be replaced with DIO sequences.
        """        


        # Ugly typecasting
        if type(pulseblocks) != list:
            self.pulseblocks = [pulseblocks]
        else:
            self.pulseblocks = pulseblocks

        self.assignment_dict = assignment_dict
        self.hd = hd
        self.template_name = template_name
        self.sequence_string = sequence_string
        self.placeholder_dict = placeholder_dict

        # Check if template is available
        if use_template:
            templates = self.get_templates(template_directory)
            if not template_name in templates:
                error_msg = f"Template name {template_name} not found. Available templates are {templates}."
                print(error_msg)

            template_filepath =  os.path.join(current_directory, template_directory, f'{template_name}.seqct')

            self.sequence_string =  open(template_filepath, 'r').read()


        

        

   