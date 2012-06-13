package Machination::XML2Assertions;

use Moose;
use namespace::autoclean;
use XML::LibXML;
use Machination::MPath;
use Text::ParseWords;
use Data::Dumper;
use Digest::SHA qw(sha256_hex);

has 'doc' => (is=>"ro",
              required=>1,
              writer=>'_set_doc');

has 'nsprefix' => (is=>"ro",
                   required=>0,
                   writer=>'_set_nsprefix');

has 'ns' => (is=>'ro',
             required=>0,
             default=>'https://github.com/machination/ns/xml2assertions');

sub BUILD {
  my $self = shift;
  my $args = shift;

  if(!ref $self->doc) {
    if($self->doc =~ /^</) {
      # interpret this as XMl in a string
      $self->_set_doc(XML::LibXML->load_xml(string => $self->doc));
    } else {
      # intpret this as a path to a file or a url
      $self->_set_doc(XML::LibXML->load_xml(location => $self->doc));
    }
  } elsif(eval {$self->doc->isa("XML::LibXML::Document")}) {
    # all fine and dandy
  } elsif(eval {$self->doc->isa("XML::LibXML::Element")}) {
    my $doc = XML::LibXML::Document->new;
    $doc->setDocumentElement($self->doc);
    $self->_set_doc($doc);
  } else {
    die "don't know how to build XML2Assertions from a " . $self->doc;
  }
  $self->_set_nsprefix($self->doc->documentElement->lookupNamespacePrefix
                       ($self->ns));
}

sub to_assertions {
  my $self = shift;
  my $node = shift;

  $node = $self->doc->documentElement unless defined $node;

#  my $mp = Machination::MPath->new($node);
#  print $mp->to_string() . "\n";

  my @a;
  my ($ass_op, $ass_arg, $action_op, $action_arg);

  # check for id generation
  if ($node->hasAttributeNS($self->ns, 'genid')) {
    my @attnames = parse_line
      ('\s+', 0, $node->getAttributeNS($self->ns, 'genid'));
    my @text;
    foreach my $name (@attnames) {
      push @text, $node->getAttribute($name);
    }
    $node->setAttribute('id', join(" ", @text));
  }
  if ($node->hasAttributeNS($self->ns, 'genidhash')) {
    my @attnames = parse_line
      ('\s+', 0, $node->getAttributeNS($self->ns, 'genidhash'));
    my @text;
    foreach my $name (@attnames) {
      push @text, $node->getAttribute($name);
    }
    $node->setAttribute('id', sha256_hex(join(" ", @text)));
  }

  # attributes
  my $atts_exist;
  foreach my $att ($node->attributes) {
    my $assert;
    my $aprefix = $att->prefix;
    my $aname = $att->nodeName;
#    print "  \@$aname\n";
    next if($aname eq "id");
    next if(defined $aprefix and $aprefix eq $self->nsprefix);
    next if(defined $aprefix and $aprefix eq "xmlns");

    my $mp = Machination::MPath->new($att);

    ($ass_op, $ass_arg, $action_op, $action_arg) = (undef);
    $ass_arg = $att->getValue;
    if($node->hasAttributeNS($self->ns, "assertAtt$aname")) {
      ($ass_op, $action_op, $action_arg) = parse_line
        ('\s+', 0, $node->getAttributeNS($self->ns, "assertAtt$aname"));
    } else {
      $ass_op = 'hastext';
      $action_op = 'settext';
    }
    push @a, {mpath=>$mp->to_string(),
              ass_op=>$ass_op,
              ass_arg=>$ass_arg,
              action_op=>$action_op,
              action_arg=>$action_arg};
    $atts_exist = 1 unless($ass_op eq 'notexists')
  }

  my $mp = Machination::MPath->new($node);

  if ($node->hasAttributeNS($self->ns, "assert")) {
#    $ass_arg = $node->textContent;
#    ($ass_op, $ass_arg, $action_op, $action_arg) = (undef);
#    ($ass_op, $action_op, $action_arg) = parse_line
    my @words;
    ($ass_op, @words) = parse_line
      ('\s+', 0, $node->getAttributeNS($self->ns, "assert"));
    if($ass_op =~ /^hastext/) {
      $ass_arg = $node->textContent;
    }
    # get the argument if there is one
    if($ass_op eq 'requires' || $ass_op eq 'excludes' ||
      $ass_op eq 'before' || $ass_op eq 'after') {
      $ass_arg = shift @words;
    }

    $action_op = shift @words;
    $action_arg = shift @words;

    # add appropriate exists assertions for ordering assertions
    my @ordering = qw(first last before after);
    if($ass_op ~~ @ordering) {
      push @a, {mpath=>$mp->to_string,
                ass_op=>"exists",
                action_op=>'create'};
      if(defined $ass_arg) {
        my $tp = Machination::MPath->new($mp);
        $tp->id($ass_arg);
        push @a, {mpath=>$tp->to_string(),
                  ass_op=>'exists',
                  action_op=>'create'};
      }
      $action_op = "reorder$ass_op";
    }

    push @a, {mpath=>$mp->to_string(),
              ass_op=>$ass_op,
              ass_arg=>$ass_arg,
              action_op=>$action_op,
              action_arg=>$action_arg};
    return \@a;
  } else {
    my $seen_textnode = 0;
    my $text = "";
    my @ch;
    foreach my $ch ($node->childNodes) {
      if($ch->nodeType == XML_ELEMENT_NODE) {
        my $a = $self->to_assertions($ch);
        push @ch, @$a if defined $a;
      }
      if($ch->nodeType == XML_TEXT_NODE) {
        $seen_textnode = 1;
        $text .= $ch->data;
      }
    }
    if (@ch) {
      push @a, @ch;
      return \@a;
    }
    if($seen_textnode) {
      push @a, {mpath=>$mp->to_string(),
                ass_op=>'hastext',
                ass_arg=>$text,
                action_op=>'settext',
               };
    } else {
      push @a, {mpath=>$mp->to_string(),
                ass_op=>'exists',
                action_op=>'create'} if (not $atts_exist);
    }
  }
  return \@a;
}

__PACKAGE__->meta->make_immutable;

1;
