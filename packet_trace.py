import time
import datetime
import tac
import collections
from tac.helper import run_exec_command, parse_cli_command


class PacketTrace(object):
    """This is a convenient class to use IOS-XE Packet Trace feature

    Args:
        interface: string, name of interface to be used as packet trace filter for conditional debug
        version: string, ipv4 or ipv6 to be used as packet trace filter for conditional debug
        acl: string, access-list to be used as packet trace filter for conditional debug
        ip_address: string, IP address to be used as packet trace filter for conditional debug
        direction: string, direction of the packet flow to be captured
        layer: string, the location that the copy of the packet starts, L2 is the default location
        drop: int, drop code
        summary_only: boolean, specifies that only the summary data is captured, default is to capture both summary data
        circular: boolean, capture last set of packets
        packet_count: int, packet count <16-8192> specifies the maximum number of packets that are maintained at one time
        fia_trace: boolean, optionally performs an FIA trace in addition to the path data info
        data_size: int, size of trace data in bytes <2048-16384>, default is 2048 bytes
        size: int, the maximum number of octets that are copied, default is 64 octets, from range <16-2048>
        copy_direction: string, direction of the packet flow to be copied
        copy: boolean, copy packet data
        punt: int, punt code
        inject: int, inject code
        mpls: mpls features -under development
        max_exec_time: int, after MAX_EXEC_TIME (sec) application will be stopped
    """

    def __init__(self, interface=None, version=None, acl=None, ip_address=None, direction='both', layer=None, drop=None,
                 summary_only=False, circular=False, packet_count=8192, fia_trace=False, data_size=None, size=None,
                 copy_direction='both', copy=False, punt=None, inject=None, mpls=False, max_exec_time=100,
                 debug_packet_commands_list=None, attach_to_the_case=True, verbose=True):
        self.interface = interface
        self.version = version
        self.acl = acl
        self.ip_address = ip_address
        self.direction = direction
        self.layer = layer
        self.drop = drop
        self.summary_only = summary_only
        self.circular = circular
        self.packet_count = packet_count
        self.fia_trace = fia_trace
        self.data_size = data_size
        self.size = size
        self.copy_direction = copy_direction
        self.copy = copy
        self.punt = punt
        self.inject = inject
        self.mpls = mpls
        self.max_exec_time = max_exec_time
        if debug_packet_commands_list is None:
            self.debug_packet_commands_list = []
        else:
            self.debug_packet_commands_list = debug_packet_commands_list
        self.configure_command = ""
        self.attach_to_the_case = attach_to_the_case
        self.verbose = verbose

    def conditions_creator(self):
        """Creates CLI command(string) to configure platform conditions with given arguments and values"""
        result = []
        if self.interface:
            result.append('interface {}'.format(self.interface))
        if self.version:
            result.append(self.version)
        if self.acl:
            result.append('access-list {}'.format(self.acl))
        if self.ip_address:
            result.append(self.ip_address)
        if self.direction:
            result.append(self.direction)
        self.configure_command = 'debug platform condition {}'.format(' '.join(result))

    def packet_trace_basic(self):
        """Creates packet trace CLI syntax and puts it in the commands list"""
        result = []
        if self.summary_only:
            result.append('summary-only')
            if self.circular:
                result.append('circular')
        else:
            if self.fia_trace:
                result.append('fia-trace')
            if self.circular:
                result.append('circular')
            if self.data_size:
                result.append('data-size {} '.format(self.data_size))
        result = 'debug platform packet-trace packet {} {}'.format(self.packet_count, ' '.join(result))
        self.debug_packet_commands_list.append(result)

    def packet_trace_copy(self):
        """Creates CLI command with copy options enabled. Appends it to commands list"""
        result = []
        if self.layer:
            result.append(self.layer)
        if self.size:
            result.append('size {}'.format(self.size))
        result = 'debug platform packet-trace copy packet {} {}'.format(self.copy_direction, ' '.join(result))
        self.debug_packet_commands_list.append(result)

    def packet_trace_drop(self):
        """Creates CLI command which enables packet trace only for dropped packets. Appends it to commands list"""
        if self.drop == 'all':
            result = 'debug platform packet-trace drop'
        else:
            result = 'debug platform packet-trace drop code {}'.format(self.drop)
        self.debug_packet_commands_list.append(result)

    def packet_trace_punt(self):
        if self.punt is not None and self.punt != 'all':
            result = 'debug platform packet-trace punt code {}'.format(self.punt)
        else:
            result = 'debug platform packet-trace punt'
        self.debug_packet_commands_list.append(result)

    def packet_trace_inject(self):
        if self.inject is not None and self.inject != 'all':
            result = 'debug platform packet-trace inject code {}'.format(self.inject)
        else:
            result = 'debug platform packet-trace inject'
        self.debug_packet_commands_list.append(result)

    def execute_command(self):
        """Executes configuration commands, also sets conditional state as Start state"""
        run_exec_command(self.configure_command)
        if self.verbose:
            print(self.configure_command)
        parsed_result = parse_cli_command('show platform conditions')
        current_debug_state = parsed_result['conditional_state']

        for command in self.debug_packet_commands_list:
            run_exec_command(command)
            if self.verbose:
                print(command)

        if current_debug_state == 'Stop':
            run_exec_command('debug platform condition start')
            if self.verbose:
                print('debug platform condition start')
            time.sleep(0.5)

    def packet_trace(self):
        """Calls functions if particular arguments are given"""
        self.conditions_creator()
        self.packet_trace_basic()
        if self.copy:
            self.packet_trace_copy()
        if self.drop:
            self.packet_trace_drop()
        if self.punt:
            self.packet_trace_punt()
        if self.inject:
            self.packet_trace_inject()
        self.execute_command()

    def run_packet_trace(self):
        """Calls self.packet_trace() method

        Terminates program either within specified period of time or after given number of packets have been captured (these
        conditions are checked every 5 seconds)

        Returns:
            url: location of file (this function saves file which contains "show platform packet-trace packet all" output on bootflash)_
        """
        self.packet_trace()
        start_time = time.time()
        while True:
            parsed_result = parse_cli_command('show platform packet-trace statistics')
            traced_packets = int(parsed_result['num_traced_packets'])
            if self.verbose:
                print('You have captured {} packets already'.format(traced_packets))
            if (traced_packets >= self.packet_count) or (time.time() - start_time > self.max_exec_time):
                if self.interface:
                    url = 'bootflash:{}_packet_trace_statistics_{}.txt'.format(
                        datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
                        self.interface.lower().replace('/', '_'))
                else:
                    url = 'bootflash:{}_packet_trace_statistics.txt'.format(
                        datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
                run_exec_command('debug platform condition stop')
                time.sleep(0.5)
                run_exec_command('show platform packet-trace packet all | redirect {}'.format(url))
                statistics = self.analyze_statistics()
                if self.verbose:
                    print('Packet Trace has been stopped')
                run_exec_command('clear platform condition all')

                result = tac.helper.Result()
                result.url = url
                result.statistics = statistics
                return result

            # TODO: add parsing feature
            else:
                time.sleep(5)

    @staticmethod
    def analyze_statistics():
        def get_flow_tuple(packet_dict):
            return (packet_dict.get('src_ip'), packet_dict.get('src_port', '0'),
                    packet_dict.get('dst_ip'), packet_dict.get('dst_port', '0'),
                    packet_dict.get('protocol', packet_dict.get('protocol_num')),
                    packet_dict.get('input_interface'),
                    packet_dict.get('drop_feature', ''))
            return

        def format_flow_tuple(flow):
            return 'Source: {}.{}, Destination: {}.{}, Protocol: {}, Interface: {}, Drop reason: {}'.format(
                *flow
            )

        result = []
        parsed_statistics = parse_cli_command('show platform packet-trace packet all')
        total = len(parsed_statistics)
        if total > 0:
            packets = collections.Counter(get_flow_tuple(packet_dict) for packet_dict in parsed_statistics)
            result.append("\n---------- Drop statistics ----------")
            for flow_tuple, i in packets.most_common():
                result.append('{}, {} out of {} packets ({:.1%})\n'.format(
                    format_flow_tuple(flow_tuple), i, total, i * 1.0 / total
                ))
        return '\n'.join(result)
