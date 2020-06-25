# pulseblock

Package for construction of pulse sequences in Jupyter Notebook.

The package consists of:
 - the main class - `PulseBlock` (in `pulse_block.py` module);
- custom-written `Pulse` classes, which are inserted into a `PulseBlock` instance (`pulse.py` module),
- several handy tools:
  - `iplot()` - function for in-line graphical visualisation of a `PulseBlock` object  
  - `pb_sample()` - function for sampling a `PulseBlock` object into time-disrcetized array for sending it to a waveform-generating device;
  - `pb_zip()` - function for collapsing large wait periods into repetitions of a single short one.
  This allows to save memory of a waveform-generating device if it supports hardware-timed sequencing mode.

`PulseBlock` is essentially a container which has several "shelves" (channels),
and each pulse is represented by a "box" (`Pulse` object) sitting on the shelf.
Each "box" must have a name tag: "channel name - start time - duration".
`PulseBlock` makes no additional assumptions about the contents of the boxes.

Since the "boxes" do not necessarily cover the entire duration, there are
some gaps. To specify what is happening during the gaps, one uses `DfltPulse`
objects - "default pulses" (a single `DfltPulse` per channel).

`PulseBlock` logic handles everything related to keeping the "boxes" time-ordered when new elements are added: it has methods for inserting additional "boxes"
into arbitrary (empty) places on the "shelf" and for merging several smaller
`PulseBlock` objects into a large one.

To get a feeling of `pulseblock` workflow, see [Tutorial Jupyter Notebook](https://nbviewer.jupyter.org/github/lukingroup/pylabnet/demo/pulseblock/pulseblock_tutorial.ipynb), also located in the demo/pulseblock directory.
