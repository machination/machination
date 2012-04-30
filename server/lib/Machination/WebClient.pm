use strict;
package Machination::WebClient;

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

use Exception::Class;
use Machination::Exceptions;
#use XML::Twig::XPath;
use Data::Dumper;
use LWP::UserAgent;
use Machination::HashXML;
use XML::LibXML;

=pod

=head1 Machination::WebClient

=head2 Synopsis

=head2 Methods:

=over

=item *e $wc = Machination::WebClient->new(%opts);

Create a new web client

=cut

sub new {
  my $class = shift;
  my %opts = @_;
  my $self = {};
  bless $self,$class;

  $self->url($opts{url});
  $self->user($opts{user}) if(exists $opts{user});
  $self->log($opts{log}) if exists $opts{log};
  $self->ua(LWP::UserAgent->new);

  return $self;
}

=item * $wc->url($url)

get or set url

=cut

sub url {
  my ($self,$in) = @_;

  if($in) {
    $self->{'url'} = $in;
  }
  return $self->{'url'};
}

=item * $wc->log($log)

get or set log object

=cut

sub log {
  my ($self,$in) = @_;

  if($in) {
    $self->{'log'} = $in;
  }
  return $self->{'log'};
}

=item * $wc->ua($ua)

get or set user agent

=cut

sub ua {
  my ($self,$in) = @_;

  if($in) {
    $self->{'ua'} = $in;
  }
  return $self->{'ua'};
}

sub user {
  my ($self,$in) = @_;

  if($in) {
    $self->{'user'} = $in;
  }
  return $self->{'user'};
}

sub call {
  my $self = shift;
  my $call = shift;

  my $xml = '<r call="' . $call . '" user="' . $self->user . '">';

  foreach (@_) {
    $xml .= to_xml(perl_to_xrep($_));
  }
  $xml .= '</r>';

  #    print "sending:\n$xml\n";

  my $res = $self->ua->post($self->url,Content=>$xml);
  unless($res->is_success) {
    WebException->throw("Error contacting web service:\n" .
                        $res->status_line . "\n");
  }

#    print $res->content;

  $xml = $res->content;

  die $self->get_error($xml) if($xml =~ /^<error>/);

  return xml_to_perl($xml);
}

sub get_error {
  my $self = shift;
  my $xml = shift;

#    my $elt = XML::Twig->new->parse($xml)->root;
  return $xml;
}

=back

=cut


1;
