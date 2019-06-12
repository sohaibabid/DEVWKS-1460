from .packet_trace import PacketTrace


class Interface(object):

    def __init__(self, parsed_data, interesting_errors):
        self.data = parsed_data
        self.errors = {}
        self.stats = {}
        self.links = {}

        self.name = parsed_data.get('interface_name')
        self.statusl1 = parsed_data.get('l1_link_status')
        self.statusl2 = parsed_data.get('l2_link_status')
        self.stats['input'] = parsed_data.get('input_packets')
        self.stats['output'] = parsed_data.get('output_packets')

        self.errors_of_interest = interesting_errors
        # self.errors_of_interest = {'input': ['input_errors',
        #                                      'input_crc',
        #                                      'input_overrun',
        #                                      'input_ignored'],
        #                            'output': ['total_output_drops',
        #                                       'output_errors']}

    def calculate_error(self, error, direction=None, number_of_errors=None, number_of_packets=None):
        if direction is None:
            print("Error direction not passed, please put input or output")  # TODO error handling
        else:
            if number_of_packets:
                packets = number_of_packets
            elif self.stats[direction] is None or self.stats[direction] == '0':
                return
            else:
                packets = self.stats[direction]

            if not number_of_errors:
                if error not in self.data:
                    return
                else:
                    errors_number = self.data[error]
            else:
                errors_number = number_of_errors

            # percent_value = self.calculate_percent(errors_number, packets)
            self.errors[error] = [errors_number, '{:.1%}'.format(float(errors_number) * 1.0 / float(packets))]

    # calculates list of errors based on the list given in errors_list
    def calculate_errors_list(self, direction):
        for error in self.errors_of_interest[direction]:
            self.calculate_error(error, direction)

    def check_queues(self):
        if 'input_queue_size' in self.data and 'input_queue_max' in self.data:
            input_queue = (self.data['input_queue_size'], self.data['input_queue_max'])
        else:
            input_queue = (None, None)

        if 'output_queue_current' in self.data and 'output_queue_max' in self.data:
            output_queue = (self.data['output_queue_current'], self.data['output_queue_max'])
        else:
            output_queue = (None, None)

        self.stats['input_queue'], self.stats['output_queue'] = input_queue, output_queue

    def show_buffers_input(self):
        # execute command to "show buffers input-interface <interface> dump"
        # dump it to the file
        # store the file link in a variable

        #  import packet_dump

        self.links['buffer_dump'] = ['/link/to/buffer/dump', ""]
        pass

    # TODO add measuring size of a capture and if it's 0 skipp the process
    def run_packet_tracer(self, mode=None):
        if mode == 'drop':
            # catch all drops for the interface
            pt = PacketTrace(interface=self.name, fia_trace=True, drop='all', max_exec_time=30, verbose=False)
            description = "File with packet tracer statistics for drops on the interface"
        else:
            # run normal packet tracer catching all packets for interface
            pt = PacketTrace(interface=self.name, fia_trace=True, max_exec_time=30, verbose=False)
            description = "File with packet tracer statistics for all packets on the interface"

        packet_tracer_result = pt.run_packet_trace()
        packet_tracer_result.description = description
        self.links['packet_tracer_result'] = packet_tracer_result

    def check_interface_health(self):
        if self.statusl1 != 'administratively down':
            self.calculate_errors_list('input')
            self.calculate_errors_list('output')
            self.check_queues()
            # TODO should running of packet trace for drops have conditions for output drops on interface?
            if self.statusl2 == 'up':
                print("Running packet tracer for the drops on the interface {}"
                      ", it will take some time".format(self.name))
                self.run_packet_tracer(mode='drop')

    def generate_health_report(self):
        result = [
            "============ {} ============".format(self.data['interface_name']),
            "Status: {}/{}".format(self.statusl1, self.statusl2)
        ]

        # interface errors
        if self.errors:
            result.append("\n---------- Interface errors ----------")
            for key, value in self.errors.items():
                result.append("{}: {} [{}]".format(key, value[0], value[1]))

        # collection links to files
        if self.links:
            result.append("\n---------- Related files ----------")
            for link in self.links.values():
                result.append('{}: "{}"'.format(link.description, link.url))
        # TODO: REWORK
        if 'packet_tracer_result' in self.links:
            result.append(self.links['packet_tracer_result'].statistics)

        result.append("\n\n")
        result = "\n".join(result)
        return result

    def present_interface_html(self):
        pass

    # def calculate_percent(self, numerator, denominator):
    #     percent_value = (format(100 * float(numerator) / int(denominator), '.2f'))
    #     return percent_value
