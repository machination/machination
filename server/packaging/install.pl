#!/usr/bin/perl

use strict;
use warnings;

use Getopt::Long qw(GetOptionsFromString);
use File::Find;
use File::Path qw(make_path);
use File::Spec;
use File::Copy;
use B qw(svref_2object);
use Text::Template;
use Pod::Usage;
use Regexp::Common;
use File::Basename;
use Cwd qw(abs_path);
use Data::Dumper;
$Data::Dumper::Indent=1;

my $tgt_root="";
my $src_root="";
my $mach_config_dir="/etc/machination";
my $mach_lib_dir="/var/lib/machination";
my $mach_log_dir="/var/log/machination";
my $default_ca_key = "$mach_config_dir/server/secrets/machination-server-ca.key";
my $default_ca_dir = "/usr/share/ca-certificates";
my $default_ca_cert = "machination-server/machination-server-ca.crt";
my $debug;
my $doit = 1;
my $manifest = 1;
my $makepkg;
my $pkgname = "machination-server";
my $scriptdir = File::Basename::dirname(abs_path(__FILE__));
my $files_tmpl_file = "$scriptdir/files.tmpl";
my $postinst_tmpl_file = "$scriptdir/machination-server.postinst.tmpl";
my $postrm_tmpl_file = "$scriptdir/machination-server.postrm.tmpl";
my $tgt_distro;
my $apache_conf_dir;

GetOptions(
           "tgt_root=s"=>\$tgt_root,
           "src_root=s"=>\$src_root,
           "debug"=>\$debug,
           "doit=i"=>\$doit,
           "manifest"=>\$manifest,
           "makepkg=s"=>\$makepkg,
           "pkgname=s"=>\$pkgname,
           "tgt_distro=s"=>\$tgt_distro,
           "files_template=s"=>\$files_tmpl_file,
           "postinst_template=s"=>\$postinst_tmpl_file,
           "apache_conf_dir=s"=>\$apache_conf_dir,
           ) || pod2usage(-verbose=>0);

my $system_perllib_dir = "/usr/share/perl5";
my $system_bin_dir = "/usr/bin";

my $files_vars =
  {
   system_perllib_dir => $system_perllib_dir,
   system_bin_dir => $system_bin_dir,
   mach_config_dir => $mach_config_dir,
   mach_lib_dir => $mach_lib_dir,
   mach_log_dir => $mach_log_dir,
  };
if(!defined $apache_conf_dir) {
  if($tgt_distro eq "debian") {
    $apache_conf_dir = "/etc/apache2/conf-available";
    $files_vars->{mach_user} = "www-data";
    $files_vars->{mach_group} = "www-data";
  } elsif($tgt_distro eq "redhat") {
    $apache_conf_dir = "/etc/httpd/conf.d";
    $files_vars->{mach_user} = "apache";
    $files_vars->{mach_group} = "apache";
  } else {
    die "Can't figure out where apache config should go";
  }
}
$files_vars->{mach_apache_conf_file} = "$apache_conf_dir/${pkgname}.conf";

my $files_tmpl = Text::Template->new(SOURCE=>$files_tmpl_file)
  or die "could not construct template from $files_tmpl_file";
my @files_lines = split("\n", $files_tmpl->fill_in(HASH=>$files_vars));
my @parsed_lines;
my $n = 1;
foreach (@files_lines) {
  # clean up the input
  s/\#.*$//; # remove comments
  s/\s+$//; # remove white space at the end of a line
  next if /^$/; # ignore empty lines

  my ($ret, $args, $opts) = parse_files_opts($_);
  die "Error at $files_tmpl_file line $n" unless($ret);
  push @parsed_lines, {args=>$args, opts=>$opts};
  $n++;
}

# wrap instrumentation around some functions
my $copy = wrap(\&File::Copy::cp);
my $make_path = wrap(\&File::Path::make_path);
my $ln = wrap(\&ln);
my $touch = wrap(\&touch);

my $cmd = $ARGV[0];
no strict "refs";
if(defined(&{"cmd_$cmd"})) {
  &{"cmd_$cmd"};
} else {
  pod2usage("unknown command \"$cmd\"");
}
exit;

sub parse_files_opts {
  my $str = shift;
  my $opts = {};
  my ($ret, $args) = GetOptionsFromString
    (
     $str,
     $opts,
     "config=s",
     "perms=s",
     "owner=s"
     );
  die
  return ($ret,$args,$opts);
}

sub cmd_deb_conffiles {
  for my $info (@parsed_lines) {
    next unless(exists $info->{opts}->{config});
    print join("\n", @{$info->{args}}) . "\n";
  }
}

sub cmd_deb_perms {
  for my $info (@parsed_lines) {
    if (exists $info->{opts}->{perms}) {
      print "chmod " . $info->{opts}->{perms} . "," . join(",", map {tgtdir($_)} @{$info->{args}}) . "\n";
      chmod(oct($info->{opts}->{perms}), map {tgtdir($_)} @{$info->{args}});
    }
  }
}

sub cmd_deb_postinst {
  my @overrides;
  for my $info (@parsed_lines) {
    my $need_override;

    # owner and group
    my ($owner, $group) = qw(root root);
    if (exists $info->{opts}->{owner}) {
      $need_override = 1;
      my ($lowner, $lgroup) = split(":",$info->{opts}->{owner});
      $owner = $lowner;
      $group = $lgroup if(defined $lgroup);
    }
    # permissions
    my $perms;
    if (exists $info->{opts}->{perms}) {
      $need_override = 1;
      $perms = $info->{opts}->{perms};
    }

    next unless($need_override);

    foreach my $f (@{$info->{args}}) {
      if(!defined $perms) {
        # Permissions not explicitly set; choose a default.
        if($f =~ s/\/$//) {
          # Directory
          $perms = "0755";
        } else {
          # File.
          $perms = "0644";
        }
      }
      push @overrides,
        "conditional_statoverride_add $owner $group $perms $f";
    }

  }

  my $post_tmpl = Text::Template->new(SOURCE=>$postinst_tmpl_file)
    or die "could not construct template from $postinst_tmpl_file";
  my $script = $post_tmpl->fill_in
    (
     HASH=>
     {
      overrides=>\@overrides,
      default_ca_key=>$default_ca_key,
      default_ca_dir=>$default_ca_dir,
      default_ca_cert=>$default_ca_cert,
     }
    );
  print $script;
}

sub cmd_deb_postrm {
  my @overrides;
  for my $info (@parsed_lines) {
    my $need_override;

    if (exists $info->{opts}->{owner}) {
      $need_override = 1;
    }
    if (exists $info->{opts}->{perms}) {
      $need_override = 1;
    }

    next unless($need_override);

    foreach my $f (@{$info->{args}}) {
      push @overrides,
        "conditional_statoverride_rm $f";
    }
  }

  my $post_tmpl = Text::Template->new(SOURCE=>$postrm_tmpl_file)
    or die "could not construct template from $postrm_tmpl_file";

  my $escaped_ca_cert = $default_ca_cert;
  $escaped_ca_cert =~ s/\//\\\//g;
  my $script = $post_tmpl->fill_in
    (
     HASH=>
     {
      overrides=>\@overrides,
      default_ca_key=>$default_ca_key,
      default_ca_dir=>$default_ca_dir,
      default_ca_cert=>$default_ca_cert,
      escaped_ca_cert=>$escaped_ca_cert,
     }
    );
  print $script;
}

sub cmd_install {
  # install perl libs
  print "installing to " . tgtdir() . " from " . srcdir() . "...\n";
  -d tgtdir() or $make_path->(tgtdir());
  find(find_install(tgtdir($system_perllib_dir),
                    {trim=>srcdir("lib"),
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
                    {trim=>srcdir("bin"),
                     ignore=>"~\$"}),
       srcdir("bin"));

  # logs
  $make_path->(tgtdir($mach_log_dir, "server", "file"));

  # empty files as placeholders for ca key and certificate
  $make_path->(tgtdir($default_ca_dir));
  $touch->(tgtdir($default_ca_key));
  $touch->(tgtdir("$default_ca_dir/$default_ca_cert"));
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

sub findsub {
  my $str = shift;
  my $hash = shift;
  # strip brackets
  my $newstr = substr($str, 1, length($str) - 2);
  if (! exists $hash->{$newstr}) {
    warn "No substitution found for $str -- leaving in place";
    return $str;
  }
  return $hash->{$newstr};
}

sub find_install {
  my $tgt = shift;
  my $opts = shift;
  $opts->{trim} = srcdir() unless exists $opts->{trim};
  return sub {
    my $dir = File::Spec->rel2abs($File::Find::dir);
    $dir =~ s/^$opts->{trim}//;
    return if(/$opts->{ignore}/);
    my $tgt_dir = File::Spec->catdir($tgt,$dir);
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
      if($name eq "make_path" or $name eq "touch") {
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
  return addroot($src_root, @_);
}

sub tgtdir {
  return addroot($tgt_root,@_);
}

sub addroot {
  my $root = shift;
  my @dirs = @_;
  unshift(@dirs, $root ) if(defined $root && $root ne "");
  return File::Spec->rel2abs(File::Spec->catdir(@dirs));
}

sub touch {
  my $file = shift;
  my $now = time;
  local (*TMP);

  utime ($now, $now, $file)
    || open (TMP, ">>$file")
      || warn ("Couldn't touch file: $!\n");
}
