# path defines
%define     configdir   %{_sysconfdir}/%{name}
%define     _sbindir    /usr/lib/frr
%define     zeb_src     %{_builddir}/%{name}-%{frrversion}
%define     zeb_rh_src  %{zeb_src}/redhat
%define     zeb_docs    %{zeb_src}/doc
%define     frr_tools   %{zeb_src}/tools

# defines for configure
%define     rundir  %{_localstatedir}/run/%{name}

############################################################################

#### Version String tweak
# Remove invalid characters form version string and replace with _
%{expand: %%global rpmversion %(echo '7.0' | tr [:blank:]- _ )}
%define         frrversion   7.0

    %global initsystem systemd

# If init system is systemd, then always enable watchfrr
%if "%{initsystem}" == "systemd"
    %global with_watchfrr 1
%endif

#### Check for RedHat 6.x or CentOS 6.x - they are too old to support PIM.
####   Always disable it on these old systems unconditionally
#
# if CentOS / RedHat and version < 7, then disable PIMd (too old, won't work)
%if 0%{?rhel} && 0%{?rhel} < 7
    %global  with_pimd  0
%endif

# misc internal defines
%{!?frr_uid:            %global  frr_uid            92 }
%{!?frr_gid:            %global  frr_gid            92 }
%{!?vty_gid:            %global  vty_gid            85 }

%define daemon_list zebra ripd ospfd bgpd isisd ripngd ospf6d pbrd bfdd watfrr bfdd
%define all_daemons %{daemon_list}

Name:           frr
Version:        7.0
Release:        1%{?dist}
Summary:        Routing daemon
License:        GPLv2+
Group:          System Environment/Daemons
Source0:        https://github.com/FRRouting/frr/releases/download/%{name}-%{version}/%{name}-%{version}.tar.xz
URL:            https://www.frrouting.org

Requires(pre):  shadow-utils

BuildRequires:  bison
BuildRequires:  c-ares-devel
BuildRequires:  flex
BuildRequires:  gcc
BuildRequires:  json-c-devel
BuildRequires:  libcap-devel
BuildRequires:  make
BuildRequires:  ncurses-devel
BuildRequires:  readline-devel
BuildRequires:  libyang-devel
BuildRequires:  python-devel >= 2.7
BuildRequires:  python-sphinx
Requires:       initscripts
BuildRequires:      systemd-devel
Requires(post):     systemd
Requires(preun):    systemd
Requires(postun):   systemd
Requires(pre):      initscripts >= 5.60


%description
FRRouting is a free software that manages TCP/IP based routing
protocol. It takes multi-server and multi-thread approach to resolve
the current complexity of the Internet.

FRRouting supports BGP4, OSPFv2, OSPFv3, ISIS, RIP, RIPng, PIM, LDP
NHRP, Babel, PBR, EIGRP and BFD.

FRRouting is a fork of Quagga.


%package contrib
Summary: contrib tools for frr
Group: System Environment/Daemons

%description contrib
Contributed/3rd party tools which may be of use with frr.


%package pythontools
Summary: python tools for frr
BuildRequires: python
Requires: python-ipaddress
Group: System Environment/Daemons

%description pythontools
Contributed python 2.7 tools which may be of use with frr.


%package devel
Summary: Header and object files for frr development
Group: System Environment/Daemons
Requires: %{name} = %{version}-%{release}

%description devel
The frr-devel package contains the header and object files neccessary for
developing OSPF-API and frr applications.


%prep
%setup -q -n frr-%{frrversion}


%build

%configure \
    --sbindir=%{_sbindir} \
    --sysconfdir=%{configdir} \
    --localstatedir=%{rundir} \
    --disable-static \
    --disable-werror \
    --disable-babeld \
    --disable-bgp-vnc \
    --disable-doc \
    --disable-eigrpd \
    --disable-fabricd \
    --disable-fpm \
    --disable-irdp \
    --disable-isisd \
    --disable-ldpd \
    --disable-nhrpd \
    --disable-ospf6d \
    --disable-ospfapi \
    --disable-ospfclient\
    --disable-ospfd \
    --disable-pbrd \
    --disable-pimd \
    --disable-ripd \
    --disable-ripngd \
    --disable-rpki \
    --disable-rtadv \
    --disable-sharpd \
    --disable-staticd \
    --enable-bfdd \
    --enable-multipath=256 \
    --enable-vtysh \
    --enable-user=frr \
    --enable-group=frr \
    --enable-vty-group=frrvty \
    --enable-watchfrr \
    --enable-cumulus \
    --enable-systemd

sed -i 's|^hardcode_libdir_flag_spec=.*|hardcode_libdir_flag_spec=""|g' libtool
sed -i 's|^runpath_var=LD_RUN_PATH|runpath_var=DIE_RPATH_DIE|g' libtool

make %{?_smp_mflags}


%install
mkdir -p %{buildroot}%{_sysconfdir}/{frr,sysconfig,logrotate.d,pam.d,default} \
         %{buildroot}%{_localstatedir}/log/frr
make DESTDIR=%{buildroot} install

# kill bogus libtool files
rm -vf %{buildroot}%{_libdir}/frr/modules/*.la
rm -vf %{buildroot}%{_libdir}/*.la
rm -vf %{buildroot}%{_libdir}/frr/libyang_plugins/*.la

# install /etc sources
mkdir -p %{buildroot}%{_unitdir}
install -m644 %{zeb_rh_src}/frr.service %{buildroot}%{_unitdir}/frr.service
install %{zeb_rh_src}/frr.init %{buildroot}%{_sbindir}/frr

install %{zeb_rh_src}/daemons %{buildroot}%{_sysconfdir}/frr
install -m644 %{zeb_rh_src}/frr.pam %{buildroot}%{_sysconfdir}/pam.d/frr
install -m644 %{zeb_rh_src}/frr.logrotate %{buildroot}%{_sysconfdir}/logrotate.d/frr
install -d -m750 %{buildroot}%{rundir}


%pre
# add vty_group
%if 0%{?vty_group:1}
    getent group %{vty_group} >/dev/null || groupadd -r -g %{vty_gid} %{vty_group}
%endif

# add frr user and group
%if 0%{?frr_user:1}
    # Ensure that frr_gid gets correctly allocated
    getent group %{frr_user} >/dev/null || groupadd -g %{frr_gid} %{frr_user}
    getent passwd %{frr_user} >/dev/null || \
    useradd -r -u %{frr_uid} -g %{frr_user} \
        -s /sbin/nologin -c "FRRouting suite" \
        -d %{rundir} %{frr_user}

    %if 0%{?vty_group:1}
        usermod -a -G %{vty_group} %{frr_user}
    %endif
%endif
exit 0


%post
# Create dummy files if they don't exist so basic functions can be used.
if [ ! -e %{configdir}/zebra.conf ]; then
    echo "hostname `hostname`" > %{configdir}/zebra.conf
%if 0%{?frr_user:1}
    chown %{frr_user}:%{frr_user} %{configdir}/zebra.conf*
%endif
    chmod 640 %{configdir}/zebra.conf*
fi
for daemon in %{all_daemons} ; do
    if [ x"${daemon}" != x"" ] ; then
        if [ ! -e %{configdir}/${daemon}.conf ]; then
            touch %{configdir}/${daemon}.conf
            %if 0%{?frr_user:1}
                chown %{frr_user}:%{frr_user} %{configdir}/${daemon}.conf*
            %endif
        fi
    fi
done
%if 0%{?frr_user:1}
    chown %{frr_user}:%{frr_user} %{configdir}/daemons
%endif

%if %{with_watchfrr}
    # No config for watchfrr - this is part of /etc/sysconfig/frr
    rm -f %{configdir}/watchfrr.*
%endif

if [ ! -e %{configdir}/vtysh.conf ]; then
    touch %{configdir}/vtysh.conf
    chmod 640 %{configdir}/vtysh.conf
%if 0%{?frr_user:1}
    %if 0%{?vty_group:1}
        chown %{frr_user}:%{vty_group} %{configdir}/vtysh.conf*
    %endif
%endif
fi


%postun
if [ "$1" -ge 1 ]; then
    %systemd_postun_with_restart frr.service
fi


%preun
    if [ $1 -eq 0 ] ; then
        %systemd_preun frr.service
    fi


%files
%doc */*.sample* COPYING
%doc doc/mpls
%doc README.md
/usr/share/yang/*.yang
%dir %attr(751,frr,frr) %{configdir}
%dir %attr(750,frr,,frr) %{_localstatedir}/log/frr
%dir %attr(751,frr,,frr) %{rundir}
%attr(750,frr,frrvty) %{configdir}/vtysh.conf.sample
%{_sbindir}/zebra
%{_sbindir}/bgpd
%exclude %{_sbindir}/ssd
%{_sbindir}/watchfrr
%{_sbindir}/bfdd
%{_libdir}/lib*.so.0
%{_libdir}/lib*.so.0.*
%{_bindir}/*
%config(noreplace) %{configdir}/[!v]*.conf*
%config(noreplace) %attr(750,%{frr_user},%{frr_user}) %{configdir}/daemons
%{_unitdir}/frr.service
%{_sbindir}/frr
%config(noreplace) %{_sysconfdir}/pam.d/frr
%config(noreplace) %{_sysconfdir}/logrotate.d/frr
%{_sbindir}/frr-reload
%{_sbindir}/frrcommon.sh
%{_sbindir}/frrinit.sh
%{_sbindir}/watchfrr.sh


%files contrib
%doc tools


%files pythontools
%{_sbindir}/frr-reload.py
%{_sbindir}/frr-reload.pyc
%{_sbindir}/frr-reload.pyo


%files devel
%{_libdir}/lib*.so
%dir %{_includedir}/%{name}
%{_includedir}/%{name}/*.h
%dir %{_includedir}/%{name}/eigrpd
%{_includedir}/%{name}/eigrpd/*.h


%changelog
* Thu Feb 28 2019 Martin Winter <mwinter@opensourcerouting.org> - %{version}
- Added libyang dependency: New work for northbound interface based on libyang
- Fabricd: New Daemon based on https://datatracker.ietf.org/doc/draft-white-openfabric/
- various bug fixes and other enhancements

* Sun Oct  7 2018 Martin Winter <mwinter@opensourcerouting.org> - 6.0
- Staticd: New daemon responsible for management of static routes
- ISISd: Implement dst-src routing as per draft-ietf-isis-ipv6-dst-src-routing
- BFDd: new daemon for BFD (Bidrectional Forwarding Detection). Responsiblei
  for notifying link changes to make routing protocols converge faster.
- various bug fixes

* Thu Jul  5 2018 Martin Winter <mwinter@opensourcerouting.org> - 5.0.1
- Support Automake 1.16.1
- BGPd: Support for flowspec ICMP, DSCP, packet length, fragment and tcp flags
- BGPd: fix rpki validation for ipv6
- VRF: Workaround for kernel bug on Linux 4.14 and newer
- Zebra: Fix interface based routes from zebra not marked up
- Zebra: Fix large zebra memory usage when redistribute between protocols
- Zebra: Allow route-maps to match on source instance
- BGPd: Backport peer-attr overrides, peer-level enforce-first-as and filtered-routes fix
- BGPd: fix for crash during display of filtered-routes
- BGPd: Actually display labeled unicast routes received
- Label Manager: Fix to work correctly behind a label manager proxy

* Thu Jun  7 2018 Martin Winter <mwinter@opensourcerouting.org> - 5.0
- PIM: Add a Multicast Trace Command draft-ietf-idmr-traceroute-ipm-05
- IS-IS: Implement Three-Way Handshake as per RFC5303
- BGPD: Implement VPN-VRF route leaking per RFC4364.
- BGPD: Implement VRF with NETNS backend
- BGPD: Flowspec
- PBRD: Add a new Policy Based Routing Daemon

* Mon May 28 2018 Rafael Zalamena <rzalamena@opensourcerouting.org> - %{version}
- Add BFDd support

* Sun May 20 2018 Martin Winter <mwinter@opensourcerouting.org>
- Fixed RPKI RPM build

* Sun Mar  4 2018 Martin Winter <mwinter@opensourcerouting.org>
- Add option to build with RPKI (default: disabled)

* Tue Feb 20 2018 Martin Winter <mwinter@opensourcerouting.org>
- Adapt to new documentation structure based on Sphinx

* Fri Oct 20 2017 Martin Winter <mwinter@opensourcerouting.org>
- Fix script location for watchfrr restart functions in daemon config
- Fix postun script to restart frr during upgrade

* Mon Jun  5 2017 Martin Winter <mwinter@opensourcerouting.org>
- added NHRP and EIGRP daemon

* Mon Apr 17 2017 Martin Winter <mwinter@opensourcerouting.org>
- new subpackage frr-pythontools with python 2.7 restart script
- remove PIMd from CentOS/RedHat 6 RPM packages (won't work - too old)
- converted to single frr init script (not per daemon) based on debian init script
- created systemd service file for systemd based systems (which uses init script)
- Various other RPM package fixes for FRR 2.0

* Fri Jan  6 2017 Martin Winter <mwinter@opensourcerouting.org>
- Renamed to frr for FRRouting fork of Quagga

* Thu Feb 11 2016 Paul Jakma <paul@jakma.org>
- remove with_ipv6 conditionals, always build v6
- Fix UTF-8 char in spec changelog
- remove quagga.pam.stack, long deprecated.

* Thu Oct 22 2015 Martin Winter <mwinter@opensourcerouting.org>
- Cleanup configure: remove --enable-ipv6 (default now), --enable-nssa,
    --enable-netlink
- Remove support for old fedora 4/5
- Fix for package nameing
- Fix Weekdays of previous changelogs (bogus dates)
- Add conditional logic to only build tex footnotes with supported texi2html
- Added pimd to files section and fix double listing of /var/lib*/quagga
- Numerous fixes to unify upstart/systemd startup into same spec file
- Only allow use of watchfrr for non-systemd systems. no need with systemd

* Fri Sep  4 2015 Paul Jakma <paul@jakma.org>
- buildreq updates
- add a default define for with_pimd

* Mon Sep 12 2005 Paul Jakma <paul@dishone.st>
- Steal some changes from Fedora spec file:
- Add with_rtadv variable
- Test for groups/users with getent before group/user adding
- Readline need not be an explicit prerequisite
- install-info delete should be postun, not preun

* Wed Jan 12 2005 Andrew J. Schorr <ajschorr@alumni.princeton.edu>
- on package upgrade, implement careful, phased restart logic
- use gcc -rdynamic flag when linking for better backtraces

* Wed Dec 22 2004 Andrew J. Schorr <ajschorr@alumni.princeton.edu>
- daemonv6_list should contain only IPv6 daemons

* Wed Dec 22 2004 Andrew J. Schorr <ajschorr@alumni.princeton.edu>
- watchfrr added
- on upgrade, all daemons should be condrestart'ed
- on removal, all daemons should be stopped

* Mon Nov 08 2004 Paul Jakma <paul@dishone.st>
- Use makeinfo --html to generate quagga.html

* Sun Nov 07 2004 Paul Jakma <paul@dishone.st>
- Fix with_ipv6 set to 0 build

* Sat Oct 23 2004 Paul Jakma <paul@dishone.st>
- Update to 0.97.2

* Sat Oct 23 2004 Andrew J. Schorr <aschorr@telemetry-investments.com>
- Make directories be owned by the packages concerned
- Update logrotate scripts to use correct path to killall and use pid files

* Fri Oct 08 2004 Paul Jakma <paul@dishone.st>
- Update to 0.97.0

* Wed Sep 15 2004 Paul Jakma <paul@dishone.st>
- build snmp support by default
- build irdp support
- build with shared libs
- devel subpackage for archives and headers

* Thu Jan 08 2004 Paul Jakma <paul@dishone.st>
- updated sysconfig files to specify local dir
- added ospf_dump.c crash quick fix patch
- added ospfd persistent interface configuration patch

* Tue Dec 30 2003 Paul Jakma <paul@dishone.st>
- sync to CVS
- integrate RH sysconfig patch to specify daemon options (RH)
- default to have vty listen only to 127.1 (RH)
- add user with fixed UID/GID (RH)
- create user with shell /sbin/nologin rather than /bin/false (RH)
- stop daemons on uninstall (RH)
- delete info file on preun, not postun to avoid deletion on upgrade. (RH)
- isisd added
- cleanup tasks carried out for every daemon

* Sun Nov 2 2003 Paul Jakma <paul@dishone.st>
- Fix -devel package to include all files
- Sync to 0.96.4

* Tue Aug 12 2003 Paul Jakma <paul@dishone.st>
- Renamed to Quagga
- Sync to Quagga release 0.96

* Thu Mar 20 2003 Paul Jakma <paul@dishone.st>
- zebra privileges support

* Tue Mar 18 2003 Paul Jakma <paul@dishone.st>
- Fix mem leak in 'show thread cpu'
- Ralph Keller's OSPF-API
- Amir: Fix configure.ac for net-snmp

* Sat Mar 1 2003 Paul Jakma <paul@dishone.st>
- ospfd IOS prefix to interface matching for 'network' statement
- temporary fix for PtP and IPv6
- sync to zebra.org CVS

* Mon Jan 20 2003 Paul Jakma <paul@dishone.st>
- update to latest cvs
- Yon's "show thread cpu" patch - 17217
- walk up tree - 17218
- ospfd NSSA fixes - 16681
- ospfd nsm fixes - 16824
- ospfd OLSA fixes and new feature - 16823
- KAME and ifindex fixes - 16525
- spec file changes to allow redhat files to be in tree

* Sat Dec 28 2002 Alexander Hoogerhuis <alexh@ihatent.com>
- Added conditionals for building with(out) IPv6, vtysh, RIP, BGP
- Fixed up some build requirements (patch)
- Added conditional build requirements for vtysh / snmp
- Added conditional to files for _bindir depending on vtysh

* Mon Nov 11 2002 Paul Jakma <paulj@alphyra.ie>
- update to latest CVS
- add Greg Troxel's md5 buffer copy/dup fix
- add RIPv1 fix
- add Frank's multicast flag fix

* Wed Oct 09 2002 Paul Jakma <paulj@alphyra.ie>
- update to latest CVS
- timestamped crypt_seqnum patch
- oi->on_write_q fix

* Mon Sep 30 2002 Paul Jakma <paulj@alphyra.ie>
- update to latest CVS
- add vtysh 'write-config (integrated|daemon)' patch
- always 'make rebuild' in vtysh/ to catch new commands

* Fri Sep 13 2002 Paul Jakma <paulj@alphyra.ie>
- update to 0.93b

* Wed Sep 11 2002 Paul Jakma <paulj@alphyra.ie>
- update to latest CVS
- add "/sbin/ip route flush proto zebra" to zebra RH init on startup

* Sat Aug 24 2002 Paul Jakma <paulj@alphyra.ie>
- update to current CVS
- add OSPF point to multipoint patch
- add OSPF bugfixes
- add BGP hash optimisation patch

* Fri Jun 14 2002 Paul Jakma <paulj@alphyra.ie>
- update to 0.93-pre1 / CVS
- add link state detection support
- add generic PtP and RFC3021 support
- various bug fixes

* Thu Aug 09 2001 Elliot Lee <sopwith@redhat.com> 0.91a-6
- Fix bug #51336

* Wed Aug  1 2001 Trond Eivind Glomsrød <teg@redhat.com> 0.91a-5
- Use generic initscript strings instead of initscript specific
  ( "Starting foo: " -> "Starting $prog:" )

* Fri Jul 27 2001 Elliot Lee <sopwith@redhat.com> 0.91a-4
- Bump the release when rebuilding into the dist.

* Tue Feb  6 2001 Tim Powers <timp@redhat.com>
- built for Powertools

* Sun Feb  4 2001 Pekka Savola <pekkas@netcore.fi>
- Hacked up from PLD Linux 0.90-1, Mandrake 0.90-1mdk and one from zebra.org.
- Update to 0.91a
- Very heavy modifications to init.d/*, .spec, pam, i18n, logrotate, etc.
- Should be quite Red Hat'isque now.
