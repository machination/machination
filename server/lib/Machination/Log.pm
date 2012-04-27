package Machination::Log;

# Copyright 2011 Colin Higgs
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

use strict;
no strict "refs";
use warnings;

use Socket;
use XML::LibXML;
use Sys::Hostname;
#use Exporter ();

#our @EXPORT = qw (SYSLOG_LEVELS);

=head1 Machination::Log

=cut

#Define constants for syslog levels
use constant SYSLOG_LEVELS =>
  {
   LOG_EMERG	=> 0	, # system is unusable
   LOG_ALERT	=> 1	, # action must be taken immediately
   LOG_CRIT	=> 2	, # critical conditions
   LOG_ERR		=> 3	, # error conditions
   LOG_WARNING	=> 4	, # warning conditions
   LOG_NOTICE	=> 5	, # normal but significant condition
   LOG_INFO	=> 6	, # informational
   LOG_DEBUG	=> 7	, # debug-level messages

   LOG_KERN	=> (0<<3)	, # kernel messages
   LOG_USER	=> (1<<3)	, # random user-level messages
   LOG_MAIL	=> (2<<3)	, # mail system
   LOG_DAEMON	=> (3<<3)	, # system daemons
   LOG_AUTH	=> (4<<3)	, # security/authorization messages
   LOG_SYSLOG	=> (5<<3)	, # messages generated internally by syslogd
   LOG_LPR		=> (6<<3)	, # line printer subsystem
   LOG_NEWS	=> (7<<3)	, # network news subsystem
   LOG_UUCP	=> (8<<3)	, # UUCP subsystem
   LOG_CRON	=> (9<<3)	, # clock daemon
   LOG_AUTHPRIV	=> (10<<3)	, # security/authorization messages (private)
   LOG_FTP		=> (11<<3)	, # ftp daemon

   LOG_LOCAL0	=> (16<<3)	, # reserved for local use
   LOG_LOCAL1	=> (17<<3)	, # reserved for local use
   LOG_LOCAL2	=> (18<<3)	, # reserved for local use
   LOG_LOCAL3	=> (19<<3)	, # reserved for local use
   LOG_LOCAL4	=> (20<<3)	, # reserved for local use
   #LOCAL5 to be used for machination
   LOG_LOCAL5	=> (21<<3)	, # reserved for local use
   LOG_LOCAL6	=> (22<<3)	, # reserved for local use
   LOG_LOCAL7	=> (23<<3)	, # reserved for local use
};

my $streams =
  {STDIN => \*STDIN,
   STDOUT => \*STDOUT,
   STDERR => \*STDERR
   };

my %valid_indents = (
                     none => undef,
                     delimeter => undef,
                     prefix => undef,
                     );

sub new {
	my $class = shift;
	my ($conf) = @_;
	my $self = {};
	bless $self,$class;

  my %opts = @_;

  $self->{message_settings} =
    {
     cat_prefix => "-",
     error => {level=>1,left=>"<",right=>">",
               syslog_priority=>SYSLOG_LEVELS->{LOG_ERR},
               ostream=>\*STDERR,
               prefix=>"ERROR:"},
     debug => {level=>1,left=>"[",right=>"]",
               syslog_priority=>SYSLOG_LEVELS->{LOG_DEBUG},
               ostream=>\*STDERR,
               prefix=>""},
     log => {level=>1,left=>"(",right=>")",
             syslog_priority=>SYSLOG_LEVELS->{LOG_INFO},
             ostream=>\*STDOUT,
             prefix=>""},
     warning => {level=>1,left=>"{",right=>"}",
                 syslog_priority=>SYSLOG_LEVELS->{LOG_WARNING},
                 ostream=>\*STDERR,
                 prefix=>"WARNING:"},
    };

  $self->syslog_facility(SYSLOG_LEVELS->{LOG_LOCAL5});
  $self->syslog_port(514);
  $self->syslog_server("localhost");

  $self->logfile("/tmp/log.txt");
  $self->progname("machination");
  $self->msg_delimeter("??");
  $self->newline_after_prefix(0);
  $self->indent("delimeter");

  $self->my_id(hostname());

  $self->use_syslog(0);
  $self->use_streams(1);
  $self->use_file(0);

	return $self;
}

sub machination_path {
  my $self = shift;
  if(@_) {
    $self->{machination_path} = shift;
  }
  return $self->{machination_path};
}

sub progname {
  my $self = shift;
  if(@_) {
    $self->{progname} = shift;
  }
  return $self->{progname};
}

sub msg_delimeter {
  my $self = shift;
  if(@_) {
    $self->{msg_delimeter} = shift;
  }
  return $self->{msg_delimeter};
}

sub newline_after_prefix {
  my $self = shift;
  if(@_) {
    $self->{newline_after_prefix} = shift;
  }
  return $self->{newline_after_prefix};
}

sub indent {
  my $self = shift;
  if(@_) {
    my $indent = shift;
    die "invalid indent: choose one of " . join(",",keys %valid_indents)
      unless(exists $valid_indents{$indent});
      $self->{indent} = $indent;
  }
  return $self->{indent};
}

sub use_syslog {
  my $self = shift;
  if(@_) {
    $self->{use_syslog} = shift;
  }
  return $self->{use_syslog};
}
sub use_streams {
  my $self = shift;
  if(@_) {
    $self->{use_streams} = shift;
  }
  return $self->{use_streams};
}
sub use_file {
  my $self = shift;
  if(@_) {
    $self->{use_file} = shift;
  }
  return $self->{use_file};
}

sub syslog_enabled {
  my $self = shift;
  return $self->{syslog_enabled};
}

sub syslog_facility {
  my $self = shift;
  if(@_) {
    my $f = shift;
    $f = SYSLOG_LEVELS->{$f} if(exists SYSLOG_LEVELS->{$f});
    $self->{syslog_facility} = $f;
  }
  return $self->{syslog_facility};
}

sub syslog_port {
  my $self = shift;
  if(@_) {
    $self->{syslog_port} = shift;
  }
  return $self->{syslog_port};
}

sub syslog_server {
  my $self = shift;
  if(@_) {
    $self->{syslog_server} = shift;
  }
  return $self->{syslog_server};
}

sub enable_syslog {
  my $self = shift;
  socket (SyslogSocket, PF_INET, SOCK_DGRAM, getprotobyname('udp'))
    or die "Can't open socket";
  $self->{syslog_enabled} = 1;
}

sub logfile {
  my $self = shift;
  if(@_) {
    $self->{logfile} = shift;
  }
  return $self->{logfile};
}

sub my_id {
  my $self = shift;
  if(@_) {
    $self->{my_id} = shift;
    #Since syslog expects a compliant hostname - replace non alnum chars
    $self->{my_id} =~ s/[[:punct:][:space:]]/X/g;
  }
  return $self->{my_id};
}

sub level {
  my $self = shift;
  my $ms = $self->{message_settings};
  if(@_) {
    my $lev = shift;
    if(ref $lev) {
      $ms->{error}->{level} = $lev->{error} if (exists $lev->{error});
      $ms->{debug}->{level} = $lev->{debug} if (exists $lev->{debug});
      $ms->{log}->{level} = $lev->{log} if (exists $lev->{log});
      $ms->{warning}->{level} = $lev->{warning} if(exists $lev->{warning});
    } else {
      $ms->{error}->{level} =
        $ms->{debug}->{level} =
          $ms->{log}->{level} =
            $ms->{warning}->{level} = $lev;
    }
  }
  return {error=>$ms->{error}->{level},
          debug=>$ms->{debug}->{level},
          log=>$ms->{log}->{level},
          warning=>$ms->{warning}->{level}};
}

sub from_xml {
  my $self = shift;
  my $xml = shift;
  if(!ref $xml) {
    my $doc = XML::LibXML->new->load_xml(string=>$xml);
    $xml = $doc->documentElement;
  }

#  print $xml->toString(1) ."\n";

  my @lm = $xml->findnodes("logMethods");
  if(@lm) {
    $self->use_streams($lm[0]->getAttribute("streams"));
    $self->use_file($lm[0]->getAttribute("file"));
    $self->use_syslog($lm[0]->getAttribute("syslog"));
  }
  my @lf = $xml->findnodes("logFile");
  if(@lf) {
    $self->logfile($lf[0]->textContent);
  }
  my @sl = $xml->findnodes("syslog");
  if(@sl) {
    my $f = $sl[0]->getAttribute("facility");
    $self->syslog_facility($f) if defined $f;
    my $p = $sl[0]->getAttribute("port");
    $self->syslog_port($p) if defined $p;
    my $s = $sl[0]->getAttribute("server");
    $self->syslog_server($s) if defined $s;
  }
  my @pn = $xml->findnodes("progname");
  if(@pn) {
    $self->progname($pn[0]->textContent);
  }
  my @md = $xml->findnodes("msgDelimeter");
  if(@md) {
    $self->msg_delimeter($md[0]->textContent);
  }
  my @nap = $xml->findnodes("newlineAfterPrefix");
  if(@nap) {
    $self->newline_after_prefix($nap[0]->textContent);
  }
  my @in = $xml->findnodes("indent");
  if(@in) {
    $self->indent($in[0]->textContent);
  }
  my @ms = $xml->findnodes("message_settings");
  if(@ms) {
    my $ms = $self->{message_settings};
    my @cp = $ms[0]->findnodes("cat_prefix");
    $ms->{cat_prefix} = $cp[0]->textContent
      if(@cp);
    foreach my $type (qw(log debug warning error)) {
      my @mt = $ms[0]->findnodes($type);
      if(@mt) {
        my $mt = $ms->{$type};
        my $lev = $mt[0]->getAttribute("level");
        $mt->{level} = $lev if defined $lev;
        my $l = $mt[0]->getAttribute("left");
        $mt->{left} = $l if defined $l;
        my $r = $mt[0]->getAttribute("right");
        $mt->{right} = $r if defined $r;
        my $pre = $mt[0]->getAttribute("prefix");
        $mt->{prefix} = $pre if defined $pre;
        my $sp = $mt[0]->getAttribute("syslog_priority");
        if(defined $sp) {
          $sp = SYSLOG_LEVELS->{$sp} if(exists SYSLOG_LEVELS->{$sp});
          $mt->{syslog_priority} = $sp;
        }
        my $os = $mt[0]->getAttribute("ostream");
        if(defined $os) {
          $os = $streams->{$os} if(exists $streams->{$os});
          $mt->{ostream} = $os;
        }
      }
    }
  }

#  return $xml;
}

sub to_xml {
  my $self = shift;

  my $log = XML::LibXML::Element->new("log");

  my $methods = $log->appendChild(XML::LibXML::Element->new("logMethods"));
  $methods->setAttribute("streams", 0+$self->use_streams);
  $methods->setAttribute("file", 0+$self->use_file);
  $methods->setAttribute("syslog", 0+$self->use_syslog);

  $log->appendTextChild("logFile",$self->logfile);

  my $syslog = $log->appendChild(XML::LibXML::Element->new("syslog"));
  my $fac;
  my $sl = SYSLOG_LEVELS;
  foreach (keys %$sl){
    $fac = $_ if(SYSLOG_LEVELS->{$_} == $self->syslog_facility);
  }
  $syslog->setAttribute("facility",$fac);
  $syslog->setAttribute("port",$self->syslog_port);
  $syslog->setAttribute("server",$self->syslog_server);

  $log->appendTextChild("progname",$self->progname);

  $log->appendTextChild("msgDelimeter",$self->msg_delimeter);

  $log->appendTextChild("newlineAfterPrefix",$self->newline_after_prefix);

  $log->appendTextChild("indent",$self->indent);

  my $ms = $log->appendChild(XML::LibXML::Element->new("message_settings"));
  $ms->appendTextChild("cat_prefix",$self->{message_settings}->{cat_prefix});

  foreach my $type (qw(log debug warning error)) {
    my $elt = $ms->appendChild(XML::LibXML::Element->new($type));
    $elt->setAttribute("level",$self->{message_settings}->{$type}->{level});
    $elt->setAttribute("left",$self->{message_settings}->{$type}->{left});
    $elt->setAttribute("right",$self->{message_settings}->{$type}->{right});
    $elt->setAttribute("prefix",$self->{message_settings}->{$type}->{prefix});
    my $pri;
    foreach (keys %$sl){
      $pri = $_ if(SYSLOG_LEVELS->{$_} ==
                   $self->{message_settings}->{$type}->{syslog_priority});
    }
    $elt->setAttribute("syslog_priority",$pri);
    my $ostream;
    foreach (keys %$streams) {
      $ostream = $_ if($streams->{$_} eq
                       $self->{message_settings}->{$type}->{ostream})
    }
    $elt->setAttribute("ostream",$ostream);
  }
  return $log;
}

sub dmsg {
  my $self = shift;
  $self->post_message(@_,"debug");
}
sub emsg {
  my $self = shift;
  $self->post_message(@_,"error");
}
sub lmsg {
  my $self = shift;
  $self->post_message(@_,"log");
}
sub wmsg {
  my $self = shift;
  $self->post_message(@_,"warning");
}

sub post_message {
  my $self = shift;
  my ($cat,$msg,$level,$type);
  $cat = "";
  if(@_ == 4) {
    ($cat,$msg,$level,$type) = @_;
  } else {
    ($msg,$level,$type) = @_;
  }
  unless(exists $self->{message_settings}->{$type}) {
    my $deb_msg = "[post_message]:" .
      "Tried to post message of unknown type \"$type\"";
    if($self->use_syslog) {
	    $self->enable_syslog unless ($self->syslog_enabled);
	    $self->send_syslog($self->syslog_facility + SYSLOG_LEVELS->{LOG_ERR},
                         $deb_msg);
    } else {
	    print STDERR "$deb_msg\n";
    }
    return undef;
  }
  my $threshold;
  if(ref $self->{message_settings}->{$type}->{"level"}) {
    $threshold = ${$self->{message_settings}->{$type}->{"level"}};
  } else {
    $threshold = $self->{message_settings}->{$type}->{"level"};
  }
  my $left = $self->{message_settings}->{$type}->{"left"};
  my $right = $self->{message_settings}->{$type}->{"right"};
  my $syslog_priority = $self->{message_settings}->{$type}->
    {"syslog_priority"};
  my $ostream = $self->{message_settings}->{$type}->{"ostream"};
  my $prefix = $self->{message_settings}->{$type}->{"prefix"};
  $msg = $self->make_message($cat,$msg,$left,$right,$prefix,$level);
  if ($threshold >= $level) {
    if ($self->use_syslog) {
	    $self->enable_syslog unless ($self->syslog_enabled);
	    $self->send_syslog($self->syslog_facility+$syslog_priority, $msg);
    }
    if ($self->use_streams) {
	    print $ostream "$msg";
    }
    if ($self->use_file) {
      my $logfile = $self->logfile;
      open (FILELOG,">>$logfile");
      print FILELOG "$msg";
      close FILELOG;
    }
  }
}

sub make_message {
  my $self = shift;
  my ($cat,$msg,$left,$right,$prefix,$level) = @_;
  $prefix = "" unless(defined $prefix);
  my $cat_prefix = $self->{message_settings}->{"cat_prefix"};
  my $line_prefix = $self->msg_delimeter . "$left" . "$level:" . $cat_prefix;
  $line_prefix .= "." if($cat);
  $line_prefix .= "$cat$right:";
  my $length;
  if ($self->indent eq "none") {
    $length = 0;
  } elsif ($self->indent eq "delimeter") {
    $length = length($self->msg_delimeter);
  } elsif ($self->indent eq "prefix") {
    $length = length($line_prefix) + 1;
  }

  $line_prefix .= " $prefix" if($prefix);
  my @lines = split(/\n/,$msg);
#  $msg = $line_prefix . " " . shift(@lines) . "\n";
  $msg = $line_prefix;
  if($self->newline_after_prefix) {
    $msg .="\n";
  } else {
    $msg .= " " . shift(@lines) . "\n";
  }
  foreach (@lines) {
    $msg .= sprintf("%${length}s%s\n","",$_);
  }
  return $msg;
}

sub send_syslog {
  my $self = shift;
  my $syslog_level = shift;
  my $msg = shift;

  my $ipaddr = inet_aton($self->syslog_server);
  my $portaddr = sockaddr_in($self->syslog_port, $ipaddr);

  # strip day of week and year from localtime
  my $timestamp = substr scalar(localtime), 4, 15;

  #Set a syslog 'hostname' if $self->my_id is broken
  $self->my_id("err-Hostname_" . hostname())
    if (! defined $self->my_id || $self->my_id eq "");

  $self->my_id("err-Unknown")
    if (! defined $self->my_id || $self->my_id eq "");

  my $log_head = "<$syslog_level>$timestamp " . $self->my_id . " " .
    $self->progname . ": ";
  my $head_length = length($log_head);
  my $chunk_length = 1023 - $head_length;
  my @msg = split(/\n/, $msg);

  foreach my $line(@msg) {
    my @lines;
    while (length($line) > 0 ) {
	    if (length($line) < $chunk_length) {
        send(SyslogSocket, $log_head . $line, 0, $portaddr);
        last;
	    }
	    #break on chunk length and replace chunk with empty string
	    my $chunk = substr($line,0,$chunk_length,"");
	    send(SyslogSocket, $log_head . $chunk, 0, $portaddr);
    }
  }
}

1;
