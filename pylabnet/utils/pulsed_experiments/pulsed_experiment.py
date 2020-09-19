
import os 
from pylabnet.hardware.awg.zi_hdawg import Driver, Sequence, AWGModule
from pylabnet.utils.zi_hdawg_pulseblock_handler.zi_hdawg_pb_handler import DIOPulseBlockHandler


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
  
        # Create Sequence Object and replace placeholder.
        seq = Sequence(
            hdawg_driver = self.hd,
            sequence = self.sequence_string,
            placeholder_dict=self.placeholder_dict
        )

        return seq

    def replace_dio_commands(self, pulseblock, dio_command_number):
        
        # Instanciate pulseblock handler.
        pb_handler = DIOPulseBlockHandler(
            pb = pulseblock,
            assignment_dict=self.assignment_dict,
            hd=self.hd
        )

        # Generate .seqc instruction set which represents pulse sequence.
        dig_pulse_sequence = pb_handler.get_dio_sequence()

        # Construct replacement dict
        dio_replacement_dict = {
            f"{self.dio_seq_identifier}{dio_command_number}", dig_pulse_sequence
        }



    def prepare_sequence(self):
        """Prepares sequence"""

        # First replace the standard placeholder.
        if self.placeholder_dict is not None: 
            self.replace_placeholders()

        # Then replace the DIO commands:
        for i, pulseblock in enumerate(self.pulseblocks):
            self.replace_dio_commands(pulseblock, i)

    

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
        self.dio_seq_identifier = dio_seq_identifier

        # Check if template is available, and store it.
        if use_template:
            templates = self.get_templates(template_directory)
            if not template_name in templates:
                error_msg = f"Template name {template_name} not found. Available templates are {templates}."
                print(error_msg)

            template_filepath =  os.path.join(
                os.path.dirname(os.path.realpath(__file__)), 
                template_directory, 
                f'{template_name}.seqct'
            )

            self.sequence_string =  open(template_filepath, 'r').read()

        # If no tempalte given, use argument input.
        else:
            self.sequence_string = template_filepath


        

        

   