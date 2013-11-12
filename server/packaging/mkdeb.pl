#!/usr/bin/perl

use Getopt::Long;
use Git;
use File::Path qw(make_path);
use File::Copy;
use Cwd qw(abs_path);
use File::Basename;
use IPC::Open3;

my $pkgname = "machination-server";
my $repo = Git->repository(".");
my $pkgver = $repo->command_oneline("describe");
my $build_dir = "/tmp/deb-packaging";

GetOptions(
           "build_dir=s"=>\$build_dir,
           );

$mach_dir = dirname(abs_path(__FILE__ . "/../.."));

-d "$build_dir" || make_path($build_dir) ||
  die "could not find or make $build_dir";

my $src_tar = "${pkgname}_${pkgver}.orig.tar.gz";

system "rm -rf $build_dir/${pkgname}*";

system "tar cfz $build_dir/$src_tar -C $mach_dir --transform 's/^server/${pkgname}_${pkgver}/' server";

system "(cd $build_dir && tar xfz $src_tar)";

system "(cd $build_dir/${pkgname}_${pkgver} && debuild -us -uc)";
