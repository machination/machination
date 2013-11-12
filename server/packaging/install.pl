#!/usr/bin/perl

use strict;
use warnings;

use Getopt::Long;
use File::Find;
use File::Path qw(make_path);
use File::Spec;
use File::Copy;
use B qw(svref_2object);
use Text::Template;
use Pod::Usage;

my $tgt_root="";
my $src_root="";
my $mach_config_dir="/etc/machination";
my $mach_lib_dir="/var/lib/machination";
my $mach_log_dir="/var/log/machination";
my $debug;
my $doit = 1;
my $manifest = 1;
my $makepkg;
my $mach_version = qx'git describe --tags --long | sed \'s/-\\([0-9]\\+\\)-.*$/\\.\\1/\'';
chomp $mach_version;
my $pkgname = "machination-server";

GetOptions(
           "tgt_root=s"=>\$tgt_root,
           "src_root=s"=>\$src_root,
           "debug"=>\$debug,
           "doit"=>\$doit,
           "manifest"=>\$manifest,
           "makepkg=s"=>\$makepkg,
           "pkgname=s"=>\$pkgname,
           ) || pod2usage(-verbose=>0);

my $system_perllib_dir = "/usr/share/perl5";
my $system_bin_dir = "/usr/bin";

# wrap instrumentation around some functions
my $copy = wrap(\&File::Copy::cp);
my $make_path = wrap(\&File::Path::make_path);
my $ln = wrap(\&ln);

my $vars =
  {
   mach_version=>$mach_version,
  };

my $cmd = $ARGV[0];
no strict "refs";
if(defined(&{"cmd_$cmd"})) {
  &{"cmd_$cmd"};
} else {
  pod2usage("unknown command \"$cmd\"");
}
exit;


sub cmd_install {
  # install perl libs
  print "installing to " . tgtdir() . "...\n";
  -d tgtdir() or $make_path->(tgtdir());
  find(find_install(tgtdir($system_perllib_dir),
                    {remove_leading=>1,
                     ignore=>"~\$"}),
       srcdir("lib"));

  # install machination config files
  $make_path->(tgtdir("$mach_config_dir","server"));
  $copy->(srcdir("packaging","default-server-config.xml"),
          tgtdir("$mach_config_dir","server","config.xml"));
  $make_path->(tgtdir("$mach_config_dir","server","secrets"));
  $copy->(srcdir("packaging","default-dbcred.xml"),
          tgtdir("$mach_config_dir","server","secrets","dbcred.xml"));

  # database files
  find(find_install(tgtdir($mach_lib_dir,"server",),
                    {ignore=>"~\$"}),
       srcdir("database"));
  $copy->(srcdir("database","bootstrap_hierarchy.hda",),
          tgtdir($mach_config_dir,"server","bootstrap_hierarchy.hda"));

  # commands
  find(find_install(tgtdir($system_bin_dir),
                    {remove_leading=>1,
                     ignore=>"~\$"}),
       srcdir("bin"));

  # logs
  $make_path->(tgtdir($mach_log_dir, "server", "file"));
}

sub cmd_configure_apache {
  if(-d "/etc/apache2/conf-available") {
    # Debian-ish
    $make_path->(tgtdir("/etc/apache2/conf-available"));
    $make_path->(tgtdir("/etc/apache2/conf-enabled"));
    $copy->(srcdir("packaging","default-mod-perl-machination.conf"),
            tgtdir("/etc/apache2/conf-available","machination.conf"));
    $ln->("../conf-available/machination.conf",tgtdir("/etc/apache2/conf-enabled/machination.conf"));
  } elsif(-d "/etc/httpd/conf.d") {
    # RedHat-ish
    $make_path->(tgtdir("/etc/httpd/conf.d"));
    $copy->(srcdir("packaging","default-mod-perl-machination.conf"),
            tgtdir("/etc/httpd/conf.d","machination.conf"));
  } else {
    die "Don't know how to install web config for this distro or OS";
  }
}

sub cmd_fix_owner_perms {

}

sub cmd_rpm_owner_perms {

}

sub cmd_rpm_config_files {

}

sub find_install {
  my $tgt = shift;
  my $opts = shift;
  return sub {
    my $dir = $File::Find::dir;
#    print "checking $dir\n";
    if ($opts->{remove_leading}) {
      my @dirs = File::Spec->splitdir($dir);
      for(1..$opts->{remove_leading}) {shift @dirs}
      $dir = File::Spec->catdir(@dirs);
    }
    return if(/$opts->{ignore}/);
    my $tgt_dir;
    if($dir) {
      $tgt_dir = File::Spec->catdir($tgt,$dir);
    } else {
      $tgt_dir = "$tgt";
    }
    if(-d "$_") {
      $make_path->(File::Spec->catfile($tgt_dir,$_));
    } else {
      $copy->($_, File::Spec->catfile($tgt_dir,$_));
    }
  };
}

sub wrap {
  my $fn = shift;
  my $name;
  $name = svref_2object($fn)->GV->NAME;
  return sub {
    print "dbg: $name " . join(",", @_) . "\n" if($debug);
    if($manifest) {
      if($name eq "copy" or $name eq "cp" or $name eq "ln") {
        print $_[1] . "\n";
      }
      if($name eq "make_path") {
        print $_[0] . "/\n";
      }
    }
    if($doit) {
      $fn->(@_);
    }
  };
}

sub ln {
  return symlink($_[0],$_[1]);
}

sub srcdir {
  return dirname($src_root, @_);
}

sub tgtdir {
  return dirname($tgt_root,@_);
}

sub dirname {
  my $root = shift;
  my @dirs = @_;
  unshift(@dirs, $root ) if(defined $root && $root ne "");
  return File::Spec->rel2abs(File::Spec->catdir(@dirs));
}
