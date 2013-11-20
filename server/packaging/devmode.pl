#!/usr/bin/perl

=pod

=head1 NAME

devmode - make changes to machination server install such that it uses
development code.

=cut

use warnings;
use strict;
use Getopt::Long;
use Pod::Usage;
use Data::Dumper;
use XML::LibXML;
use File::Spec;
use Cwd qw(abs_path);
use File::Temp;
use File::Copy;

my $lib = "lib";
my $apache_conf = "/etc/apache2/conf-available/machination-server.conf";
my $mach_config_dir = "/etc/machination";
my $db_username = "machination";
my $db_pass = "!workingyet";

=head1 SYNOPSIS

As someone with permission to edit various config files:

devmode.pl --lib lib

=cut

GetOptions(
           $lib=>\$lib,
           ) or die pod2usage();

my $libdir = abs_path($lib);
print "using library path $libdir\n";

print "\n\n";

print "checking $apache_conf\n";
my $tmp = File::Temp->new();
open(my $ah, "<", $apache_conf) or die $!;
my $seen_perlswitches;
my $altered;
while(<$ah>) {
  if(/^\s*PerlSwitches/) {
    # PerlSwitches directive already there: make sure it has -I/our/lib/dir
    $seen_perlswitches = 1;
    if(! /-I$libdir/) {
      $_ .= " -I$libdir\n";
      chomp;
      $altered = 1;
    }
  }
  print $tmp $_;
}
if(! $seen_perlswitches) {
  print $tmp "\nPerlSwitches -I$libdir\n";
  $altered = 1;
}
close $tmp;
if($altered) {
  print "altering $apache_conf...\n ...making copy in ${apache_conf}.predev\n";
  copy($apache_conf, "${apache_conf}.predev");
  copy($tmp->filename, $apache_conf);
}
$altered = 0;

print "\n\n";

print "Finding debug mode in $mach_config_dir/server/config.xml\n";
my $doc = XML::LibXML->load_xml(location=>"$mach_config_dir/server/config.xml");
my $hsubconf = ($doc->findnodes('//subconfig[@xml:id="subconfig.haccess"]'))[0]
  or die "Could not find subconfig 'subconfig.haccess'";
if(! $hsubconf->findvalue('@debug')) {
  print "Debug mode not currently set: setting.\n";
  $hsubconf->setAttribute("debug",1);
  open(my $fh, ">$mach_config_dir/server/config.xml");
  print $fh $doc->toString;
  close $fh;
}

print "\n\n";

print "Setting admin user to 'dev' in $mach_config_dir/server/bootstrap_hierarchy.hda\n";
$tmp = File::Temp->new();
open(my $fh, "<", "$mach_config_dir/server/bootstrap_hierarchy.hda") or die $!;
$altered = 0;
while(<$fh>) {
  s/setvar\(_USER_,.*\)/setvar\(_USER_,dev\)/;
  print $tmp $_;
}
close $tmp;
copy($tmp->filename, "$mach_config_dir/server/bootstrap_hierarchy.hda");

print "\n\n";

print "chmod 755 $mach_config_dir/server/secrets\n";
chmod(0755, "$mach_config_dir/server/secrets");
print "chmod 644 $mach_config_dir/server/secrets/dbcred.xml\n";
chmod(0644, "$mach_config_dir/server/secrets/dbcred.xml");
