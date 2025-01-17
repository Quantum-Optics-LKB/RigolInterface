# How to install gpib on linux

This tuto was inspired by the following readings;

- https://gist.github.com/ochococo/8362414fff28fa593bc8f368ba94d46a
- https://tomverbeure.github.io/2023/01/29/Installing-Linux-GPIB-Drivers-for-the-Agilent-82357B.html
- https://xdevs.com/guide/ni_gpib_rpi/
- https://linux-gpib.sourceforge.io/doc_html/supported-hardware.html#NI-USB-HS
- https://github.com/fmhess/hsplus_load
- https://github.com/fmhess/linux_gpib_firmware/tree/master/ni_gpib_usb_hsp
- 

In the commands do:

```bash
sudo apt-get install tk-dev build-essential texinfo texi2html libcwidget-dev libncurses5-dev libx11-dev binutils-dev bison flex libusb-1.0-0 libusb-dev libmpfr-dev libexpat1-dev tofrodos subversion autoconf automake libtool mercurial
svn checkout svn://svn.code.sf.net/p/linux-gpib/code/trunk linux-gpib-code
cd ~/linux-gpib-code/linux-gpib-kernel
make
sudo make install
cd linux-gpib-code/linux-user
./bootstrap
./configure --sysconfdir=/etc
make
sudo make install
```
Then leave this folder. In an other folder:

```bash
git clone https://github.com/fmhess/hsplus_load.git
cd hsplus_load
sudo apt-get install libusb-1.0-0-dev
sudo make
sudo chmod u+x hsplus_load
```

Then, go to https://github.com/fmhess/linux_gpib_firmware/tree/master/ni_gpib_usb_hsp and download ni_gpib_usb_hsp_stage1.bin and ni_gpib_usb_hsp_stage2.bin in the same folder where the make was done.

Back in the commands:

```bash
sudo ./hsplus_load ni_gpib_usb_hsp_stage1.bin ni_gpib_usb_hsp_stage2.bin
sudo modprobe ni_usb_gpib
sudo ldconfig

```

And in /etc/gpib.conf, replace the interface{...} by :

```bash
interface {
            minor = 0       /* board index, minor = 0 uses /dev/gpib0, minor = 1 uses /dev/gpib1, etc. */
            board_type = "ni_usb_b" /* type of interface board being used */
            name = "usb-hs" /* optional name, allows you to get a board descriptor using ibfind() */
            pad = 0 /* primary address of interface             */
            sad = 0 /* secondary address of interface           */
            timeout = T3s   /* timeout for commands */

            eos = 0x0a      /* EOS Byte, 0xa is newline and 0xd is carriage return */
            set-reos = yes  /* Terminate read if EOS */
            set-bin = no    /* Compare EOS 8-bit */
            set-xeos = no   /* Assert EOI whenever EOS byte is sent */
            set-eot = yes   /* Assert EOI with last byte on writes */

            master = yes    /* interface board is system controller */
    }
```

Back in the commands:

```bash
sudo gpib_config
sudo chmod 777 /dev/gpib*
```

As for the authorizations, modify /etc/udev/rules.d/98-gpib-generic.rules (for exemple with `sudo gedit /etc/udev/rules.d/98-gpib-generic.rules`). Replace `GROUP="gpib"` by `GROUP="[user_name]"` with [user_name] being replaced by your user name under linux. For example, for me it gives :`GROUP="aspect-15b"`
