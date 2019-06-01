import plotly.offline as pltly
import plotly.graph_objs as graph_objs
pltly.init_notebook_mode()


def iplot(pb_obj, use_gl=False):

    # Do nothing for empty PulseBlock
    if len(pb_obj.dflt_dict.keys()) == 0 and len(pb_obj.p_dict.keys()) == 0:
        return None

    # Iterate through p_dict.keys() and dflt_dict.keys()
    # and create a trace for each channel
    #  - create sorted list of channels
    d_ch_set = set(pb_obj.dflt_dict.keys())
    p_ch_set = set(pb_obj.p_dict.keys())
    ch_list = list(d_ch_set | p_ch_set)
    ch_list.sort()

    # - iterate trough ch_list
    trace_list = []
    for ch_index, ch in enumerate(ch_list):

        #
        # Build x_ar, y_ar, text_ar
        #

        # initial zero-point - default pulse object printout
        x_ar = [0]
        y_ar = [ch_index]
        if ch in pb_obj.dflt_dict.keys():
            text_ar = [
                '{}'.format(
                    str(pb_obj.dflt_dict[ch])
                )
            ]
        else:
            text_ar = ['']

        # Iterate through pulse list and create a rectangular
        # arc for each pulse. The mid-point on the upper segment
        # contains printout of the pulse object
        if ch in pb_obj.p_dict.keys():
            for p_item in pb_obj.p_dict[ch]:
                # edges of the pulse
                t1 = p_item.t0
                t2 = p_item.t0 + p_item.dur

                # left vertical line
                if t1 == 0:
                    # If pulse starts at the origin,
                    # do not overwrite (x=0, y=ch_index) point
                    # which contains dflt_dict[ch] printout
                    x_ar.append(t1)
                    y_ar.append(ch_index + 0.8)
                else:
                    x_ar.extend([t1, t1])
                    y_ar.extend([ch_index, ch_index + 0.8])

                # mid-point, which will contain printout
                x_ar.append((t1 + t2) / 2)
                y_ar.append(ch_index + 0.8)

                # right vertical line
                x_ar.extend([t2, t2])
                y_ar.extend([ch_index + 0.8, ch_index])

                # set mid-point text to object printout
                if t1 == 0:
                    # If pulse starts at the origin,
                    # do not overwrite (x=0, y=ch_index) point
                    # which contains dflt_dict[ch] printout
                    text_ar.extend(
                        [
                            '{:.2e}'.format(t1),
                            '{}'.format(str(p_item)),
                            '{:.2e}'.format(t2),
                            '{:.2e}'.format(t2)
                        ]
                    )
                else:
                    text_ar.extend(
                        [
                            '{:.2e}'.format(t1),
                            '{:.2e}'.format(t1),
                            '{}'.format(str(p_item)),
                            '{:.2e}'.format(t2),
                            '{:.2e}'.format(t2)
                        ]
                    )

        # final zero-point
        x_ar.append(pb_obj.dur)
        y_ar.append(ch_index)
        text_ar.append('{:.2e}'.format(pb_obj.dur))

        #
        # END: Build x_ar, y_ar, text_ar
        #

        # Create trace for 'ch'
        if use_gl:
            # For a large PulseBlock (above 10k pulses)- use WebGL module
            # Notice that there is a limit on number of WebGL objects in a
            # notebook (about 7-9), so use this mode for large blocks only
            trace = graph_objs.Scattergl(
                x=x_ar,
                y=y_ar,
                text=text_ar,
                hoverinfo='text',
                mode="lines",
                name=ch
            )
        else:
            # Standard Scatter for not too large PulseBlock objects
            trace = graph_objs.Scatter(
                x=x_ar,
                y=y_ar,
                text=text_ar,
                hoverinfo='text',
                mode="lines",
                name=ch
            )
        trace_list.append(trace)

    # Create figure
    fig = graph_objs.Figure(data=trace_list)

    fig['layout'].update(title='{}'.format(pb_obj.name))
    fig['layout'].update(height=100 + 100 * len(ch_list), width=800)
    fig['layout']['yaxis'].update(showticklabels=False)
    fig['layout']['legend'].update(traceorder='reversed')
    fig['layout'].update(hovermode='closest')

    # Display figure
    config_dict = {
        'showLink': False,
        'displaylogo': False
    }
    pltly.iplot(figure_or_data=fig, config=config_dict)
