#!/usr/bin/perl

# Copyright 2008 Colin Higgs and Matthew Richardson
#
# This file is part of Machination.
#
# Machination is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Machination is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Machination.  If not, see <http://www.gnu.org/licenses/>.

use lib qw(lib);
use Machination::WebClient;
use Data::Dumper;
$Data::Dumper::Indent=1;
use Getopt::Long;
Exception::Class::Base->Trace(1);

$|=1;

my $user;
GetOptions(
    "user=s"=>\$user
    );
$user = getpwuid($>) unless(defined $user);

my $wc = Machination::WebClient->
  new(url=>'http://localhost/machination/hierarchy/',
      user=>$user);

my $call = shift @ARGV;

my @args;
foreach (@ARGV) {
    if(s/^s://) {
	push @args,$_;
    } elsif(s/^h://) {
	push @args, eval "{$_}";
    } elsif(s/^a://) {
	push @args, eval "[$_]";
    } else {
	push @args,$_;
    }
}

my $result = $wc->call($call,@args);

print Dumper($result);
