use strict;
package Machination::DBAccessor;

# Copyright 2008 Colin Higgs
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

use Exception::Class;
use Exception::Class::DBI;
use Machination::Exceptions;
use Machination::ConfigFile;
#use XML::Twig;
use DBI;

use Data::Dumper;

=pod

=head1 Machination::DBAccessor

=head2 Enable low level access to the machination database

=head2 Synopsis

    $conf = Machination::ConfigFile->
      new('/path/to/config/file');
    $dba = Machination::DBAccessor->new($conf);

    or

    $dba = Machination::DBAccessor->new('path/to/config/file');

=head2 Machination::DBAccessor

=head3 Methods:

=over

=item * $dba = Machination::DBAccessor->new($conf)

    Create a new Machination::DBaccessor

    $conf is either /path/to/config/file or a
    Machination::ConfigFile object

=cut

sub new {
    my $class = shift;
    my ($conf) = @_;
    my $self = {};
    bless $self,$class;
    $self->conf($conf) if(defined $conf);
    if($self->db_string &&
       $self->db_username &&
       $self->db_password) {
        # we have enough info to make a connection
	$self->connect;
    }
    return $self;
}

=item * $conf = $self->conf

    get/set conf

=cut

sub conf {
  my $self = shift;
  my ($conf) = @_;

  if($conf) {
    if(! ref($conf)) {
	    $self->{conf} = Machination::ConfigFile->new($conf);
    } elsif($conf->isa("Machination::ConfigFile")) {
	    $self->{conf} = $conf;
    } else {
	    ConfigException->
        throw("$conf is not the right type to be stored in conf");
    }
  }

  return $self->{conf};
}

sub dbh {
    my $self = shift;
    if(@_) {$self->{dbh} = shift}
    return $self->{dbh}
}

sub db_cred {
    my $self = shift;
    unless($self->{cred}) {
	my $doc = $self->conf->parser->
	    parse_file($self->conf->get_file("file.database.CREDENTIALS"));
	$self->{cred} = $doc->documentElement;
    }
    return $self->{cred};
}

sub db_username {
    my $self = shift;
    return ($self->db_cred->findnodes("username"))[0]->textContent;
}

sub db_password {
    my $self = shift;
    return ($self->db_cred->findnodes("password"))[0]->textContent;
}

sub connect {
    my $self = shift;
    eval {
	$self->{'dbh'} = DBI->
	    connect($self->db_string,
		    $self->db_username,
		    $self->db_password,
		    {RaiseError=>0,
		     HandleError=>Exception::Class::DBI->handler,
		     PrintError=>0,
		     AutoCommit=>1,
		     }
		    );
    };
    if(my $e = $@) {
	DBIException->
	    throw(error=>"Could not open connection to database:\n$e",
		  ex_object=>$e);
    }
    return $self->{'dbh'};
}

sub db_string {
    my $self = shift;

    my $dbname = $self->conf->
	get_value('subconfig.database','connection/database');
    my $host = $self->conf->
	get_value('subconfig.database','connection/server');
    my $port = $self->conf->
	get_value('subconfig.database','connection/port');
    my $driver_name = $self->conf->
	get_value('subconfig.database','connection/driver');

    my $dbstr = "dbi";
    if($driver_name eq "Pg") {
	$dbstr .= ":Pg";
	DBSourceStringException->throw("no database name\n")
	    unless($dbname);
	$dbstr .= ":dbname=$dbname";
	$dbstr .= ";host=$host" if($host);
	$dbstr .= ";port=$port" if($port);
    } else {
	DBSourceStringException->throw("unknown driver type " .
				       "\"$driver_name\"\n");
    }
    return $dbstr;
}

sub db_arr_str_to_array {
    my $self = shift;
    my $str = shift;

    my @arr;

    $str =~s/^{//;
    $str =~s/}$//;
    @arr = split(/,/,$str);

    wantarray ? return @arr : return \@arr;
}

=back

=cut

1;
