#!/usr/bin/env python
"""

Copyright (c) 2014-2018 Alex Forencich

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""

from myhdl import *
import os

import axis_ep

module = 'axis_fifo'
testbench = 'test_%s' % module

srcs = []

srcs.append("../rtl/%s.v" % module)
srcs.append("%s.v" % testbench)

src = ' '.join(srcs)

build_cmd = "iverilog -o %s.vvp %s" % (testbench, src)

def bench():

    # Parameters
    DEPTH = 4
    DATA_WIDTH = 8
    KEEP_ENABLE = (DATA_WIDTH>8)
    KEEP_WIDTH = (DATA_WIDTH/8)
    LAST_ENABLE = 1
    ID_ENABLE = 1
    ID_WIDTH = 8
    DEST_ENABLE = 1
    DEST_WIDTH = 8
    USER_ENABLE = 1
    USER_WIDTH = 1
    FRAME_FIFO = 0
    USER_BAD_FRAME_VALUE = 1
    USER_BAD_FRAME_MASK = 1
    DROP_BAD_FRAME = 0
    DROP_WHEN_FULL = 0

    # Inputs
    clk = Signal(bool(0))
    rst_dut = Signal(bool(0))
    current_test = Signal(intbv(0)[8:])

    s_axis_tdata = Signal(intbv(0)[DATA_WIDTH:])
    s_axis_tkeep = Signal(intbv(1)[KEEP_WIDTH:])
    s_axis_tvalid = Signal(bool(0))
    s_axis_tlast = Signal(bool(0))
    s_axis_tid = Signal(intbv(0)[ID_WIDTH:])
    s_axis_tdest = Signal(intbv(0)[DEST_WIDTH:])
    s_axis_tuser = Signal(intbv(0)[USER_WIDTH:])
    m_axis_tready = Signal(bool(0))

    # Outputs
    s_axis_tready = Signal(bool(0))
    m_axis_tdata = Signal(intbv(0)[DATA_WIDTH:])
    m_axis_tkeep = Signal(intbv(1)[KEEP_WIDTH:])
    m_axis_tvalid = Signal(bool(0))
    m_axis_tlast = Signal(bool(0))
    m_axis_tid = Signal(intbv(0)[ID_WIDTH:])
    m_axis_tdest = Signal(intbv(0)[DEST_WIDTH:])
    m_axis_tuser = Signal(intbv(0)[USER_WIDTH:])

    # sources and sinks
    rst_tb = Signal(bool(0))
    source_pause = Signal(bool(0))
    sink_pause = Signal(bool(0))

    source = axis_ep.AXIStreamSource()

    source_logic = source.create_logic(
        clk,
        rst_tb,
        tdata=s_axis_tdata,
        tkeep=s_axis_tkeep,
        tvalid=s_axis_tvalid,
        tready=s_axis_tready,
        tlast=s_axis_tlast,
        tid=s_axis_tid,
        tdest=s_axis_tdest,
        tuser=s_axis_tuser,
        pause=source_pause,
        name='source'
    )

    sink = axis_ep.AXIStreamSink()

    sink_logic = sink.create_logic(
        clk,
        rst_tb,
        tdata=m_axis_tdata,
        tkeep=m_axis_tkeep,
        tvalid=m_axis_tvalid,
        tready=m_axis_tready,
        tlast=m_axis_tlast,
        tid=m_axis_tid,
        tdest=m_axis_tdest,
        tuser=m_axis_tuser,
        pause=sink_pause,
        name='sink'
    )

    # DUT
    if os.system(build_cmd):
        raise Exception("Error running build command")

    dut = Cosimulation(
        "vvp -m myhdl %s.vvp -lxt2" % testbench,
        clk=clk,
        rst=rst_dut,
        current_test=current_test,

        s_axis_tdata=s_axis_tdata,
        s_axis_tkeep=s_axis_tkeep,
        s_axis_tvalid=s_axis_tvalid,
        s_axis_tready=s_axis_tready,
        s_axis_tlast=s_axis_tlast,
        s_axis_tid=s_axis_tid,
        s_axis_tdest=s_axis_tdest,
        s_axis_tuser=s_axis_tuser,

        m_axis_tdata=m_axis_tdata,
        m_axis_tkeep=m_axis_tkeep,
        m_axis_tvalid=m_axis_tvalid,
        m_axis_tready=m_axis_tready,
        m_axis_tlast=m_axis_tlast,
        m_axis_tid=m_axis_tid,
        m_axis_tdest=m_axis_tdest,
        m_axis_tuser=m_axis_tuser
    )

    @always(delay(4))
    def clkgen():
        clk.next = not clk

    @instance
    def check():
        yield delay(100)
        yield clk.posedge
        rst_dut.next = 1
        rst_tb.next = 1
        yield clk.posedge
        rst_dut.next = 0
        rst_tb.next = 0
        yield clk.posedge
        yield delay(100)
        yield clk.posedge

        yield clk.posedge

        yield clk.posedge
        print("test 1: test packet")
        current_test.next = 1

        test_frame = axis_ep.AXIStreamFrame(
            b'\xDA\xD1\xD2\xD3\xD4\xD5' +
            b'\x5A\x51\x52\x53\x54\x55' +
            b'\x80\x00' +
            b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10',
            id=1,
            dest=1
        )

        source.send(test_frame)

        yield sink.wait()
        rx_frame = sink.recv()

        assert rx_frame == test_frame

        yield delay(100)

        yield clk.posedge
        print("test 2: longer packet")
        current_test.next = 2

        test_frame = axis_ep.AXIStreamFrame(
            b'\xDA\xD1\xD2\xD3\xD4\xD5' +
            b'\x5A\x51\x52\x53\x54\x55' +
            b'\x80\x00' +
            bytearray(range(256)),
            id=2,
            dest=1
        )

        source.send(test_frame)

        yield sink.wait()
        rx_frame = sink.recv()

        assert rx_frame == test_frame

        yield clk.posedge
        print("test 3: test packet with pauses")
        current_test.next = 3

        test_frame = axis_ep.AXIStreamFrame(
            b'\xDA\xD1\xD2\xD3\xD4\xD5' +
            b'\x5A\x51\x52\x53\x54\x55' +
            b'\x80\x00' +
            b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10',
            id=3,
            dest=1
        )

        source.send(test_frame)
        yield clk.posedge

        yield delay(64)
        yield clk.posedge
        source_pause.next = True
        yield delay(32)
        yield clk.posedge
        source_pause.next = False

        yield delay(64)
        yield clk.posedge
        sink_pause.next = True
        yield delay(32)
        yield clk.posedge
        sink_pause.next = False

        yield sink.wait()
        rx_frame = sink.recv()

        assert rx_frame == test_frame

        yield delay(100)

        yield clk.posedge
        print("test 4: back-to-back packets")
        current_test.next = 4

        test_frame1 = axis_ep.AXIStreamFrame(
            b'\xDA\xD1\xD2\xD3\xD4\xD5' +
            b'\x5A\x51\x52\x53\x54\x55' +
            b'\x80\x00' +
            b'\x01\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10',
            id=4,
            dest=1
        )
        test_frame2 = axis_ep.AXIStreamFrame(
            b'\xDA\xD1\xD2\xD3\xD4\xD5' +
            b'\x5A\x51\x52\x53\x54\x55' +
            b'\x80\x00' +
            b'\x02\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10',
            id=4,
            dest=2
        )

        source.send(test_frame1)
        source.send(test_frame2)

        yield sink.wait()
        rx_frame = sink.recv()

        assert rx_frame == test_frame1

        yield sink.wait()
        rx_frame = sink.recv()

        assert rx_frame == test_frame2

        yield delay(100)

        yield clk.posedge
        print("test 5: alternate pause source")
        current_test.next = 5

        test_frame1 = axis_ep.AXIStreamFrame(
            b'\xDA\xD1\xD2\xD3\xD4\xD5' +
            b'\x5A\x51\x52\x53\x54\x55' +
            b'\x80\x00' +
            b'\x01\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10',
            id=5,
            dest=1
        )
        test_frame2 = axis_ep.AXIStreamFrame(
            b'\xDA\xD1\xD2\xD3\xD4\xD5' +
            b'\x5A\x51\x52\x53\x54\x55' +
            b'\x80\x00' +
            b'\x02\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10',
            id=5,
            dest=2
        )

        source.send(test_frame1)
        source.send(test_frame2)
        yield clk.posedge

        while s_axis_tvalid or m_axis_tvalid:
            yield clk.posedge
            yield clk.posedge
            source_pause.next = False
            yield clk.posedge
            source_pause.next = True
            yield clk.posedge

        source_pause.next = False

        yield sink.wait()
        rx_frame = sink.recv()

        assert rx_frame == test_frame1

        yield sink.wait()
        rx_frame = sink.recv()

        assert rx_frame == test_frame2

        yield delay(100)

        yield clk.posedge
        print("test 6: alternate pause sink")
        current_test.next = 6

        test_frame1 = axis_ep.AXIStreamFrame(
            b'\xDA\xD1\xD2\xD3\xD4\xD5' +
            b'\x5A\x51\x52\x53\x54\x55' +
            b'\x80\x00' +
            b'\x01\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10',
            id=6,
            dest=1
        )
        test_frame2 = axis_ep.AXIStreamFrame(
            b'\xDA\xD1\xD2\xD3\xD4\xD5' +
            b'\x5A\x51\x52\x53\x54\x55' +
            b'\x80\x00' +
            b'\x02\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10',
            id=6,
            dest=2
        )

        source.send(test_frame1)
        source.send(test_frame2)
        yield clk.posedge

        while s_axis_tvalid or m_axis_tvalid:
            sink_pause.next = True
            yield clk.posedge
            yield clk.posedge
            yield clk.posedge
            sink_pause.next = False
            yield clk.posedge

        yield sink.wait()
        rx_frame = sink.recv()

        assert rx_frame == test_frame1

        yield sink.wait()
        rx_frame = sink.recv()

        assert rx_frame == test_frame2

        yield delay(100)

        yield clk.posedge
        print("test 7: tuser assert")
        current_test.next = 7

        test_frame = axis_ep.AXIStreamFrame(
            b'\xDA\xD1\xD2\xD3\xD4\xD5' +
            b'\x5A\x51\x52\x53\x54\x55' +
            b'\x80\x00' +
            b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10',
            id=7,
            dest=1,
            last_cycle_user=1
        )

        source.send(test_frame)

        yield sink.wait()
        rx_frame = sink.recv()

        assert rx_frame == test_frame
        assert rx_frame.last_cycle_user

        yield delay(100)

        yield clk.posedge
        print("test 8: initial sink pause")
        current_test.next = 8

        test_frame = axis_ep.AXIStreamFrame(
            b'\x01\x02\x03',
            id=8,
            dest=1
        )

        sink_pause.next = 1
        source.send(test_frame)
        yield clk.posedge
        yield clk.posedge
        yield clk.posedge
        yield clk.posedge
        sink_pause.next = 0

        yield sink.wait()
        rx_frame = sink.recv()

        assert rx_frame == test_frame

        yield delay(100)

        yield clk.posedge
        print("test 9: initial sink pause, reset")
        current_test.next = 9

        test_frame = axis_ep.AXIStreamFrame(
            b'\x01\x02\x03',
            id=9,
            dest=1
        )

        sink_pause.next = 1
        source.send(test_frame)
        yield clk.posedge
        yield clk.posedge
        yield clk.posedge
        yield clk.posedge

        rst_dut.next = 1
        rst_tb.next = 1
        yield clk.posedge
        rst_dut.next = 0
        rst_tb.next = 0

        sink_pause.next = 0

        yield delay(100)

        yield clk.posedge
        yield clk.posedge
        yield clk.posedge

        assert sink.empty()

        yield delay(100)

        yield clk.posedge
        print("test 10: backpressure test")
        current_test.next = 10

        test_frame = axis_ep.AXIStreamFrame(
            b'\xDA\xD1\xD2\xD3\xD4\xD5' +
            b'\x5A\x51\x52\x53\x54\x55' +
            b'\x80\x00' +
            bytearray(range(256)),
            id=10,
            dest=1
        )

        sink_pause.next = 1
        source.send(test_frame)
        source.send(test_frame)
        yield delay(5000)
        yield clk.posedge
        sink_pause.next = 0

        yield sink.wait()
        rx_frame = sink.recv()

        assert rx_frame == test_frame

        yield sink.wait()
        rx_frame = sink.recv()

        assert rx_frame == test_frame

        yield delay(100)

        yield clk.posedge
        print("test 11: many small packets")
        current_test.next = 11

        test_frame = axis_ep.AXIStreamFrame(
            b'\xAA',
            id=11,
            dest=1
        )

        for k in range(64):
            source.send(test_frame)

        for k in range(64):
            yield sink.wait()
            rx_frame = sink.recv()

            assert rx_frame == test_frame

        yield delay(100)

        yield clk.posedge
        print("test 12: reset")
        current_test.next = 12

        # send data without reading it
        sink_pause.next = 1

        test_frame = axis_ep.AXIStreamFrame(
            b'\x80\x00',
            id=1,
            dest=1
        )

        source.send(test_frame)

        yield delay(100)

        # prepare second frame, but don't send it yet
        test_frame = axis_ep.AXIStreamFrame(
            b'\xAA\xBB',
            id=2,
            dest=2
        )

        source_pause.next = 1

        source.send(test_frame)

        # reset the FIFO
        yield clk.posedge
        rst_dut.next = 1

        # start tranmission immediately after reset
        source_pause.next = 0
        yield clk.posedge
        rst_dut.next = 0

        # receive test frame
        sink_pause.next = 0

        yield sink.wait()
        rx_frame = sink.recv()

        assert rx_frame == test_frame

        yield delay(100)

        raise StopSimulation

    return instances()

def test_bench():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sim = Simulation(bench())
    sim.run()

if __name__ == '__main__':
    print("Running test...")
    test_bench()

