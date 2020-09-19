

class PulsedExperiment():

    def __init__(self, hd, pulseblock, assignment_dict, 
    use_template=True, template_name='base_dig_pulse', sequence_string=None):
        """ Initilizes pulseblock experiment

        :hd: Instance of ZI AWG Driver
        :pulseblock_objects: Single Pulseblock object or list of Pulseblock
                    objects.
        :assignment_dict: Assigning channels to DIO output bins.
        :use_template: (bool) If True, look for .seqc template, if false, use
            sequence_string 
        :template_name: (str) Name of the .seqc template file (must be stored in sequence_template_folders)
        :sequence_string: (str) .seqc sequence if no template sequence is used.
        """
        pass
   