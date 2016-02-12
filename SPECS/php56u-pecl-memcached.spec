%global with_zts    0%{?__ztsphp:1}
%global with_tests  %{?_with_tests:1}%{!?_with_tests:0}
%global pecl_name   memcached
%global real_name   php-pecl-memcached
%global php_base    php56u
# After 40-igbinary, 40-json
%global ini_name    50-%{pecl_name}.ini

Summary:      Extension to work with the Memcached caching daemon
Name:         %{php_base}-pecl-%{pecl_name}
Version:      2.2.0
Release:      5.ius%{?dist}
# memcached is PHP, FastLZ is MIT
License:      PHP and MIT
Group:        Development/Languages
URL:          http://pecl.php.net/package/%{pecl_name}
Source0:      http://pecl.php.net/get/%{pecl_name}-%{version}.tgz
BuildRequires: %{php_base}-devel
BuildRequires: %{php_base}-pear
BuildRequires: %{php_base}-pecl-jsonc-devel
BuildRequires: %{php_base}-pecl-igbinary-devel
#BuildRequires: libevent-devel  > 2
BuildRequires: libevent-devel
%if 0%{?rhel} && 0%{?rhel} < 7
BuildRequires: libmemcached10-devel >= 1.0.10
%else
BuildRequires: libmemcached-devel >= 1.0.10
%endif
BuildRequires: zlib-devel
BuildRequires: cyrus-sasl-devel
%if %{with_tests}
BuildRequires: memcached
%endif

Requires(post): %{php_base}-pear
Requires(postun): %{php_base}-pear

Requires:     %{php_base}-json%{?_isa}
Requires:     %{php_base}-pecl-igbinary%{?_isa}
Requires:     %{php_base}(zend-abi) = %{php_zend_api}
Requires:     %{php_base}(api) = %{php_core_api}

Provides:     php-%{pecl_name} = %{version}
Provides:     php-%{pecl_name}%{?_isa} = %{version}
Provides:     php-pecl(%{pecl_name}) = %{version}
Provides:     php-pecl(%{pecl_name})%{?_isa} = %{version}

Provides:     %{php_base}-%{pecl_name} = %{version}
Provides:     %{php_base}-%{pecl_name}%{?_isa} = %{version}
Provides:     %{php_base}-pecl(%{pecl_name}) = %{version}
Provides:     %{php_base}-pecl(%{pecl_name})%{?_isa} = %{version}

Provides: %{real_name} = %{version}
Conflicts: %{real_name} < %{version}

%if 0%{?fedora} < 20 && 0%{?rhel} < 7
# Filter private shared
%{?filter_provides_in: %filter_provides_in %{_libdir}/.*\.so$}
%{?filter_setup}
%endif


%description
This extension uses libmemcached library to provide API for communicating
with memcached servers.

memcached is a high-performance, distributed memory object caching system,
generic in nature, but intended for use in speeding up dynamic web
applications by alleviating database load.

It also provides a session handler (memcached).


%prep
%setup -c -q

mv %{pecl_name}-%{version} NTS

# Check version as upstream often forget to update this
extver=$(sed -n '/#define PHP_MEMCACHED_VERSION/{s/.* "//;s/".*$//;p}' NTS/php_memcached.h)
if test "x${extver}" != "x%{version}"; then
   : Error: Upstream HTTP version is now ${extver}, expecting %{version}.
   : Update the pdover macro and rebuild.
   exit 1
fi

cat > %{ini_name} << 'EOF'
; Enable %{pecl_name} extension module
extension=%{pecl_name}.so

; ----- Options to use the memcached session handler

; RPM note : save_handler and save_path are defined
; for mod_php, in /etc/httpd/conf.d/php.conf
; for php-fpm, in /etc/php-fpm.d/*conf

;  Use memcache as a session handler
;session.save_handler=memcached
;  Defines a comma separated list of server urls to use for session storage
;session.save_path="localhost:11211"

; ----- Configuration options
; http://php.net/manual/en/memcached.configuration.php

EOF

# default options with description from upstream
cat NTS/memcached.ini >>%{ini_name}

%if %{with_zts}
cp -r NTS ZTS
%endif


%build
peclconf() {
%configure --enable-memcached-igbinary \
           --enable-memcached-json \
           --enable-memcached-sasl \
           --with-php-config=$1
}
cd NTS
%{_bindir}/phpize
peclconf %{_bindir}/php-config
%{__make} %{?_smp_mflags}

%if %{with_zts}
cd ../ZTS
%{_bindir}/zts-phpize
peclconf %{_bindir}/zts-php-config
%{__make} %{?_smp_mflags}
%endif


%install
# Install the NTS extension
%{__make} install -C NTS INSTALL_ROOT=%{buildroot}

# Drop in the bit of configuration
%{__install} -D -m 644 %{ini_name} %{buildroot}%{php_inidir}/%{ini_name}

# Install XML package description
%{__install} -D -m 644 package.xml %{buildroot}%{pecl_xmldir}/%{name}.xml

# Install the ZTS extension
%if %{with_zts}
%{__make} install -C ZTS INSTALL_ROOT=%{buildroot}
%{__install} -D -m 644 %{ini_name} %{buildroot}%{php_ztsinidir}/%{ini_name}
%endif

# Test & Documentation
cd NTS
for i in $(grep 'role="test"' ../package.xml | sed -e 's/^.*name="//;s/".*$//')
do %{__install} -Dpm 644 $i %{buildroot}%{pecl_testdir}/%{pecl_name}/$i
done
for i in $(grep 'role="doc"' ../package.xml | sed -e 's/^.*name="//;s/".*$//')
do %{__install} -Dpm 644 $i %{buildroot}%{pecl_docdir}/%{pecl_name}/$i
done


%post
%{pecl_install} %{pecl_xmldir}/%{name}.xml >/dev/null || :


%postun
if [ $1 -eq 0 ] ; then
    %{pecl_uninstall} %{pecl_name} >/dev/null || :
fi


%check
OPT="-n"
[ -f %{php_extdir}/igbinary.so ] && OPT="$OPT -d extension=igbinary.so"
[ -f %{php_extdir}/json.so ]     && OPT="$OPT -d extension=json.so"
[ -f %{php_extdir}/msgpack.so ]  && OPT="$OPT -d extension=msgpack.so"

: Minimal load test for NTS extension
%{__php} $OPT \
    -d extension=%{buildroot}%{php_extdir}/%{pecl_name}.so \
    --modules | grep %{pecl_name}

%if %{with_zts}
: Minimal load test for ZTS extension
%{__ztsphp} $OPT \
    -d extension=%{buildroot}%{php_ztsextdir}/%{pecl_name}.so \
    --modules | grep %{pecl_name}
%endif

%if %{with_tests}
ret=0

: Launch the Memcached service
memcached -p 11211 -U 11211      -d -P $PWD/memcached.pid

: Run the upstream test Suite for NTS extension
pushd NTS
rm tests/flush_buffers.phpt tests/touch_binary.phpt
TEST_PHP_EXECUTABLE=%{__php} \
TEST_PHP_ARGS="$OPT -d extension=$PWD/modules/%{pecl_name}.so" \
NO_INTERACTION=1 \
REPORT_EXIT_STATUS=1 \
%{__php} -n run-tests.php || ret=1
popd

%if %{with_zts}
: Run the upstream test Suite for ZTS extension
pushd ZTS
rm tests/flush_buffers.phpt tests/touch_binary.phpt
TEST_PHP_EXECUTABLE=%{__ztsphp} \
TEST_PHP_ARGS="$OPT -d extension=$PWD/modules/%{pecl_name}.so" \
NO_INTERACTION=1 \
REPORT_EXIT_STATUS=1 \
%{__ztsphp} -n run-tests.php || ret=1
popd
%endif

# Cleanup
if [ -f memcached.pid ]; then
   kill $(cat memcached.pid)
fi

exit $ret
%endif


%files
%doc %{pecl_docdir}/%{pecl_name}
%doc %{pecl_testdir}/%{pecl_name}
%{pecl_xmldir}/%{name}.xml
%config(noreplace) %{php_inidir}/%{ini_name}
%{php_extdir}/%{pecl_name}.so

%if %{with_zts}
%config(noreplace) %{php_ztsinidir}/%{ini_name}
%{php_ztsextdir}/%{pecl_name}.so
%endif


%changelog
* Fri Feb 12 2016 Carl George <carl.george@rackspace.com> - 2.2.0-5.ius
- Change minimum libmemcached version to 1.0.10 (upstream GH#25)
- Clean up libmemcached build requirement logic

* Mon Oct 27 2014 Ben Harper <ben.harper@rackspace.com> - 2.2.0-4.ius
- porting from php55u-pecl-memcached

* Fri Oct 10 2014 Carl George <carl.george@rackspace.com> - 2.2.0-3.ius
- Conflict with stock package
- Provide stock package

* Tue Sep 30 2014 Carl George <carl.george@rackspace.com> - 2.2.0-2.ius
- Sync with EPEL7 package
- add numerical prefix to extension configuration file
- add all ini options in configuration file (comments)
- install doc in pecl doc_dir
- install tests in pecl test_dir
- enable ZTS extension
- rebuilt with igbinary support
- add arch specific provides/requires
- add filter_provides to avoid private-shared-object-provides memcached.so
- add minimal %%check

* Wed Sep 10 2014 Carl George <carl.george@rackspace.com> - 2.2.0-1.ius
- Latest upstream

* Fri Dec 06 2013 Ben Harper <ben.harper@rackspace.com> -  2.1.0-4.ius
- porting from php54-pecl-memcached

* Wed Nov 06 2013 Ben Harper <ben.harper@rackspace.com> -  2.1.0-3.ius
- adding provides per LB bug 1052542 comment #28

* Tue Nov 13 2012 Ben Harper <ben.harper@rackspace.com> -  2.1.0-2.ius
- building off libmemcached10-1.0.13-2

* Thu Nov 01 2012 Ben Harper <ben.harper@rackspace.com> - 2.1.0-1.ius
- porting from php53u-pecl-memcached
- updated release to 2.1.0

* Thu Jan 19 2012 Jeffrey Ness <jeffrey.ness@rackspace.com> - 1.0.0-2
- Porting from EPEL to IUS

* Sat Jan 29 2011 Remi Collet <fedora@famillecollet.com> - 1.0.0-1
- EL-5 build, fix BR for php abi

* Sun Jul 12 2009 Remi Collet <fedora@famillecollet.com> - 1.0.0-1
- Update to 1.0.0 (First stable release)

* Sat Jun 27 2009 Remi Collet <fedora@famillecollet.com> - 0.2.0-1
- Update to 0.2.0 + Patch for HAVE_JSON constant

* Wed Apr 29 2009 Remi Collet <fedora@famillecollet.com> - 0.1.5-1
- Initial RPM

