
import os
from pylabnet.hardware.awg.zi_hdawg import Driver, Sequence, AWGModule
from pylabnet.utils.zi_hdawg_pulseblock_handler.zi_hdawg_pb_handler import AWGPulseBlockHandler

class PulsedExperiment():
    """ Wrapper class for Pulsed experiments using the ZI HDAWG.
    This class conveniently allows for the generation and the AWG upload of
    pulse-sequences.
    """

    def get_templates(self, template_directory="sequence_templates"):
        """Look in sequence template folder and return list of templates."""

        # Get all relevant files template files
        current_directory = os.path.dirname(os.path.realpath(__file__))

        template_directory = os.path.join(current_directory, template_directory)

        files = [file for file in os.listdir(template_directory)
            if  '.seqct' in file and '__init__.py' not in file
        ]

        files_trimmed = [filename.replace('.seqct', '') for filename in files]

        return files_trimmed

    def replace_placeholders(self):
        """Replace all sequence placeholders with values."""
        self.seq.replace_placeholders(self.placeholder_dict)
        self.hd.log.info("Replaced placeholders.")

    def replace_awg_commands(self, pulseblock):
        """Replace all waveform placeholders with actual AWG waveform commands.

        :pulseblock: Pulseblock object
        """

        if self.iplot:
            from pylabnet.utils.pulseblock.pb_iplot import iplot
            iplot(pulseblock)

        # Instanciate pulseblock handler.
        pb_handler = AWGPulseBlockHandler(
            pb = pulseblock,
            assignment_dict=self.assignment_dict,
            exp_config_dict=self.exp_config_dict,
            hd=self.hd
        )

        # Generate instruction set which represents pulse sequence.
        prologue_sequence, pulse_sequence, upload_waveforms = pb_handler.get_awg_sequence(len(self.upload_waveforms))

        # Replace the pulseblock name placeholder with the generated instructions
        self.seq.replace_placeholders({pulseblock.name : pulse_sequence})
        self.seq.prepend_sequence(prologue_sequence)
        
        # Save the list of waveforms to be uploaded to AWG
        self.upload_waveforms.extend(upload_waveforms)

        self.hd.log.info("Replaced waveform placeholder sequence(s).")

        return pb_handler

    def prepare_sequence(self):
        """Prepares sequence by replacing all variable placeholders and waveform-placeholders."""

        # First replace the standard placeholders
        if self.placeholder_dict is not None:
            self.replace_placeholders()

        # Then replace the waveform commands
        for pulseblock in self.pulseblocks:
            pb_handler = self.replace_awg_commands(pulseblock)
            self.pulseblock_handlers.append(pb_handler)

    def prepare_awg(self, awg_number):
        """ Create AWG instance, uploads sequence and configures DIO output bits

        :awg_nuber: (int) Core number of AWG to be started.
        """

        # Create an instance of the AWG Module.
        awg = AWGModule(self.hd, awg_number)

        if awg is None:
            return

        awg.set_sampling_rate('2.4 GHz') # Set 2.4 GHz sampling rate.
        self.hd.log.info("Preparing to upload sequence.")

        # Upload sequence
        awg.compile_upload_sequence(self.seq)

        # Upload waveforms to AWG
        for index, waveform_tuple in enumerate(self.upload_waveforms):
            waveform_np_array = waveform_tuple[-1]
            awg.dyn_waveform_upload(index, waveform_np_array)

        # Setup analog channel settings for each pulseblock
        # Setup DIO drive bits for each pulseblock
        for pb_handler in self.pulseblock_handlers:
            awg.setup_dio(pb_handler.DIO_bits)
            awg.setup_analog(pb_handler.setup_config_dict, self.assignment_dict)

        return awg

    def prepare_microwave(self):
        """ Command the microwave generator to turn on output and set the 
        oscillator frequency based on the IQ pulse requirements. """

        if self.mw_client is None:
            return

        # Get all specified LO frequencies from the IQ pulses 
        lo_freqs = set()
        for pb_handler in self.pulseblock_handlers:
            if "lo_freq" in pb_handler.setup_config_dict:
                lo_freqs.add(pb_handler.setup_config_dict["lo_freq"])

        if len(lo_freqs) == 0:
            self.hd.log.info("MW client available but no pulses requiring MW oscillator.")
            return
        elif len(lo_freqs) > 1:
            self.hd.log.warn("More than 1 MW frequencies specified, taking the first one.")

        self.mw_client.set_freq(list(lo_freqs)[0])
        # mw_client.set_power() # TODO: any default value for powers?
        self.mw_client.output_on()

    def get_ready(self, awg_number):
        """Prepare AWG for sequence execution.

        This function will generate the sequence based on the placeholders and the
        pulseblocks, upload it to the AWG and configure the DIO output bits.
        """
        self.prepare_sequence()
        self.prepare_microwave()
        return self.prepare_awg(awg_number) # TODO YQ

    def __init__(self, 
                pulseblocks, 
                assignment_dict, 
                hd, 
                mw_client=None,
                placeholder_dict=None,
                exp_config_dict=None,
                use_template=True, 
                template_name='base_dig_pulse', 
                sequence_string=None,
                marker_string='$',
                template_directory="sequence_templates", 
                iplot=True):
        """ Initilizes pulseblock experiment

        :pulseblocks: Single Pulseblock object or list of Pulseblock objects.
        :assignment_dict: Assigning channel numbers to channel names. 
            Format: {channel_name : [ "analog"/"dio", channel_number ]}
        :hd: Instance of ZI AWG Driver
        :placeholder_dict: Dictionary containing placeholder names and values for the .seqct file.
        :exp_config_dict: Dictionary containing any additional configs.
        :use_template: (bool) If True, look for .seqc template, if false, use
            sequence_string .
        :template_name: (str) Name of the .seqct template file (must be stored in sequence_template_folders)
        :sequence_string: (str) .seqc sequence if no template sequence is used.
        :marker_string: (str) String used to wrap placeholders to indicate them for replacement.
        :template_directory: Folder where to look for .seqct templates.
        :iplot: If True, sequences will be plotted.
        """

        # Ugly typecasting
        if type(pulseblocks) != list:
            self.pulseblocks = [pulseblocks]
        else:
            self.pulseblocks = pulseblocks

        # List of pulseblock handlers
        self.pulseblock_handlers = []

        self.assignment_dict = assignment_dict
        self.hd = hd
        self.mw_client = mw_client
        self.template_name = template_name
        self.sequence_string = sequence_string
        self.marker_string = marker_string
        self.placeholder_dict = placeholder_dict
        self.exp_config_dict = exp_config_dict
        self.iplot = iplot

        # List of waveforms to be uploaded. Items are of the form:
        # tuple(waveform var name, ch_name, start_step, end_step, np.array waveform)
        self.upload_waveforms = []

        # Check if template is available, and store it.
        if use_template:
            templates = self.get_templates(template_directory)
            if not template_name in templates:
                error_msg = f"Template name {template_name} not found. Available templates are {templates}."
                self.hd.log.error(error_msg)

            template_filepath =  os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                template_directory,
                f'{template_name}.seqct'
            )
            sequence_string =  open(template_filepath, 'r').read()
            self.hd.log.info(f"Using template {template_name}.seqc")

        # If no template given, use argument input.
        else:
            sequence_string = sequence_string
            self.hd.log.info("Using user input sequence.")

        # Initialize sequence object.
        self.seq = Sequence(
            hdawg_driver = hd,
            sequence = sequence_string,
            marker_string = marker_string
        )
