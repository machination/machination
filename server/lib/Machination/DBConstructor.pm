use strict;
package Machination::DBConstructor;

# Copyright 2010 Colin Higgs
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Machination.	 If not, see <http://www.gnu.org/licenses/>.

use Carp;
use Exception::Class;
use Machination::Exceptions;
use Machination::DBAccessor;
use XML::LibXML;
use DB::Config;

use Data::Dumper;

use constant {
	ID_TYPE => 'bigserial',
	IDREF_TYPE => 'bigint',
	OBJECT_NAME_TYPE => "varchar",
	OBJECT_NAMEREF_TYPE => "varchar",
};

@Machination::DBConstructor::ISA = qw(Machination::DBAccessor);

=pod

	=head1 Machination::DBConstructor

	=over

	=cut


#sub new {
#		 my $class = shift;
#		 my $self = $class->SUPER::new(@_);
#		 bless $self,$class;
#		 $self->dbh->{AutoCommit} = 0;
#		 return $self;
#}

=item * $dbh = $con->connect;

call SUPER::Connect and then set AutoCommit to 0

=cut

sub connect {
	my $self = shift;
	my $dbh = $self->SUPER::connect(@_);
	$self->dbh->{AutoCommit} = 0;
	return $dbh;
}

=item * $parser = $con->parser

=cut

sub parser {
	my $self = shift;
	$self->{parser} = shift if(@_);
	$self->{parser} = XML::LibXML->new unless($self->{parser});
	return $self->{parser};
}

=item * $con->dbconfig
	accessor for internal DB::Config object

=cut

sub dbconfig {
	my $self = shift;
	$self->{dbconfig} = shift if(@_);
	unless($self->{dbconfig}) {
		$self->{dbconfig} = DB::Config->new($self->dbh);
		$self->{dbconfig}->schema_path(
			$self->conf->get_dir('dir.DATABASE') . "/rng-schemas"
		);
		my $type_subs = XML::LibXML->load_xml(
			location=>$self->conf->get_dir('dir.DATABASE') .
			"/type-substitutions.xml"
		)->documentElement;
		$self->{dbconfig}->type_subs($type_subs);
	}

	return $self->{dbconfig};
}

=item * $con->config_base_tables

=cut

sub config_base_tables {
	my $self = shift;

	my @tables =
    (
     $self->gentable
     (
      {name=>'valid_ops',
			 pk=>["name"],
			 cols=>[["name","varchar"],
							["description","varchar"]],
			}
     ),
     $self->gentable
     (
			{name=>'revisions',
			 pk=>["id"],
			 cols=>[["id",ID_TYPE],
							["vop","varchar"],
							["parent",IDREF_TYPE],
							["actor","varchar"]],
			 fks=>[{table=>"valid_ops",cols=>[['vop','name']]},
						 {table=>'revisions',cols=>[['parent','id']]}],
			}
     ),
     $self->gentable
     (
			{name=>"valid_channels",
			 pk=>["id"],
			 cols=>[["id",ID_TYPE],
							["name","varchar",{nullAllowed=>0}],
              ["root_tag","varchar",{nullAllowed=>0}],
              ["scratch_mpath","varchar",{nullAllowed=>0}],
              ["keep_scratch","bool",{nullAllowed=>0}]],
			 cons=>[{type=>"UNIQUE",cols=>['name']}],
			 history=>1,
			}
     ),
     $self->gentable
     (
      {name=>"valid_oses",
       pk=>["id"],
       cols=>[
              ["id",ID_TYPE],
              ["name","varchar",{nullAllowed=>0}],
              ["major_version","varchar",{nullAllowed=>0}],
              ["minor_version","varchar",{nullAllowed=>0}],
              ["bitness","int",{nullAllowed=>0}],
             ],
       cons=>[{type=>"UNIQUE",cols=>['name',
                                     'major_version',
                                     'minor_version',
                                     'bitness']}],
       history=>1,
      }
     ),
     $self->gentable
     (
      {name=>"object_types",
			 pk=>["id"],
			 cols=>[['id',ID_TYPE],
							['name','varchar',{nullAllowed=>0}],
							['plural','varchar',{nullAllowed=>0}],
							['is_entity','boolean',{nullAllowed=>0}],
							['is_attachable','boolean',{nullAllowed=>0}],
              ['agroup',IDREF_TYPE]],
       fks=>[{table=>"object_types",cols=>[["agroup","id"]]}],
			 cons=>[{type=>"UNIQUE",cols=>['name']}],
			 history=>1,
			}
     ),
     $self->gentable
     ({name=>"setmember_types",
       pk=>["type"],
       cols=>[["type","varchar"],
              ["is_internal","boolean",{nullAllowed=>0}],
              ["is_set","boolean",{nullAllowed=>0}]],
       history=>1,
      }),
     $self->gentable
     ({name=>"valid_condition_ops",
       pk=>["op"],
       cols=>[["op","varchar"]],
       history=>1,
      }),
     $self->gentable
     ({name=>"direct_conditions",
       pk=>["id"],
       cols=>[["id",ID_TYPE],
              ["set_id",IDREF_TYPE,{nullAllowed=>0}],
              ["col","name",{nullAllowed=>0}],
              ["op","varchar",{nullAllowed=>0}],
              ["val","varchar",{nullAllowed=>0}]],
       fks=>[{table=>"valid_condition_ops",cols=>[["op","op"]]}],
       history=>1,
     }),
     $self->gentable
     (
			{name=>"hcs",
			 pk=>['id'],
			 cols=>[["id",ID_TYPE],
							['parent',IDREF_TYPE],
							['name',OBJECT_NAME_TYPE,{nullAllowed=>0}],
							['ordinal','bigint',{nullAllowed=>0}],
							['is_mp','boolean',{nullAllowed=>0}],
							["owner",OBJECT_NAME_TYPE]],
			 fks=>[{table=>'hcs',cols=>[['parent','id']]}],
			 cons=>[{type=>"UNIQUE",cols=>['parent','ordinal']}],
			 history=>1,
			}
     ),
     $self->gentable
     ({name=>"valid_assertion_ops",
       pk=>["op"],
       cols=>[["op","varchar"],
              ["arg_meaning","varchar"]],
       history=>1,
      }),
#     $self->gentable
#     ({name=>"lib_assertion_ops",
#       pk=>["op"],
#       cols=>[["op","varchar"]],
#       history=>1,
#      }),
     $self->gentable
     ({name=>"valid_action_ops",
       pk=>["op"],
       cols=>[["op","varchar"],
              ["complete","boolean",{nullAllowed=>0}],
              ["overlay","boolean",{nullAllowed=>0}],
              ["arg_meaning","varchar"],
              ["description","varchar"]],
       history=>1,
      }),
#     $self->gentable
#     ({name=>"assertion_actions",
#       pk=>["id"],
#       cols=>[["id",ID_TYPE],
#              ["op","varchar",{nullAllowed=>0}],
#              ["ref","varchar"],
#              ["description","varchar"]],
#       fks=>[{table=>"action_ops",cols=>[["op","op"]]}],
#			 cons=>[{type=>"UNIQUE",cols=>["ref"]}],
#       history=>1,
#      }),
#     $self->gentable
#     ({name=>"action_args",
#       pk=>["id"],
#       cols=>[["id",ID_TYPE],
#              ["name","name",{nullAllowed=>0}],
#              ["value","varchar"],
#              ["action_id",IDREF_TYPE,{nullAllowed=>0}]],
#       fks=>[{table=>"assertion_actions",cols=>[["action_id","id"]]}],
#       history=>1,
#      }),
     $self->gentable
     ({name=>'certs',
       pk=>['serial'],
       cols=>[
              ['serial', ID_TYPE],
              ['name', 'varchar', {nullAllowed=>0}],
              ['type', 'char(1)', {nullAllowed=>0}],
              ['expiry_date', 'timestamp', {nullAllowed=>0}],
              ['rev_date', 'timestamp'],
             ],
       cons=>[{type=>'general',text=>"check (type in ('V','E','R'))"}],
      }),
    );

	$self->config_tables(@tables);
}

sub config_postobj_tables {
	my $self = shift;

	my @tables =
    (
    );

  $self->config_tables(@tables);
}

sub config_tables {
  my $self = shift;

  foreach my $t (@_) {
		print $t->toString(1) . "\n";
		$self->dbconfig->config_table_cols($t);
		$self->dbconfig->config_table_constraints($t);
		$self->dbconfig->config_table_foreign_keys($t);
		$self->dbconfig->config_table_triggers($t);
	}
}

sub register_op {
	my $self = shift;
	my ($name,$desc) = @_;

	my $existing = $self->dbh->selectall_hashref(
		"select * from valid_ops where name=?","name",{},$name);
#		 print Dumper($existing);
	if(exists $existing->{$name}) {
		$self->dbh->do("update valid_ops " .
									 "set description=? where name=?",{},$desc,$name);
	} else {
		$self->dbh->do("insert into valid_ops " .
									 "(name,description) " .
									 "values (?,?)", {}, $name, $desc);
	}
}

#sub type_exists {
#	my $self = shift;
#	my ($type) = @_;
#
#	my $sth = $self->dbh->
#			prepare_cached("select name from object_types where name=?",
#										 {dbi_dummy=>"DBConstructor.type_exists"});
#	$sth->execute($type);
#	return $sth->fetchall_hashref("name")->{$type};
#}


=item * $xml_elt = $con->rep_to_xml($rep)

	$rep = [ 'tag', [attrib=>val, ...], content1, ... ]

	becomes

	<tag attrib="val" ...>content1 ...</tag>

	contents may be text and/or sub elements

=cut

sub rep_to_xml {
	my $self = shift;
	my ($rep) = @_;

	my ($tag,$atts,@contents) = @$rep;
	my $elt = XML::LibXML::Element->new($tag);
	while(@$atts) {
		my $name = shift @$atts;
		my $value = shift @$atts;
		$elt->setAttribute($name,$value);
	}
	foreach my $c (@contents) {
		if(ref $c) {
			$elt->appendChild($self->rep_to_xml($c));
		} else {
			$elt->appendTextNode($c);
		}
	}

	return $elt;
}

sub xml_to_rep {
	my $self = shift;
	my ($xml) = @_;

	my $rep = [];
	if(!ref($xml)) {
		my $doc = $self->parser->parse_string($xml);
		$xml = $doc->documentElement;
	}
	my @att_nodes = $xml->findnodes("attribute::*");
	my @children = $xml->childNodes;

	push @$rep, $xml->nodeName;
	my @atts;
	foreach my $anode (@att_nodes) {
		push @atts, $anode->nodeName;
		push @atts, $anode->nodeType;
	}
	push @$rep, \@atts;
	foreach my $child (@children) {
		if($child->nodeType == XML_TEXT_NODE) {
			push @$rep, $child->data;
		} elsif ($child->nodeType == XML_ELEMENT_NODE) {
			push @$rep, $self->xml_to_rep($child);
		} else {
			die "don't know how to turn node of type " .
					$child->nodeType . " into an array";
		}
	}
	return $rep;
}

=item B<mach_table_to_canonical>

@canonical_table_elts = $self->mach_table_to_canonical($mach_table_elt);

Expand any extras, like making a history table element when
history='1', to make table elements suitable for DB::Config.

=cut

sub mach_table_to_canonical {
	my $self = shift;
	my $elt = shift;
	my @elts = $elt;
	my $name = $elt->getAttribute('name');

	if($elt->getAttribute('history')) {
		my $celt = XML::LibXML::Element->new('column');
		$elt->appendChild($celt);
		$celt->setAttribute('name','rev_id');
		$celt->setAttribute('type','{IDREF_TYPE}');
		my $fk = XML::LibXML::Element->new('constraint');
#		$fk->setAttribute('id',con_name($name,"fk","rev_id"));
		$fk->setAttribute('type','foreignKey');
		$fk->setAttribute('refTable','revisions');
		my @cons = $elt->getChildrenByTagName('constraint');
		my $lastcon = $cons[$#cons];
		$elt->insertAfter($fk,$lastcon);
		my $fkcol = XML::LibXML::Element->new('column');
		$fkcol->setAttribute('name', 'rev_id');
		$fkcol->setAttribute('references', 'id');
		$fk->appendChild($fkcol);

		my $htelt = XML::LibXML::Element->new("table");
		push @elts, $htelt;
		$htelt->setAttribute("name", "zzh_$name");
		my $pkelt = XML::LibXML::Element->new('primaryKey');
#		$pkelt->setAttribute('id',$self->con_name("zzh_$name","pk"));
		$htelt->appendChild($pkelt);
		my $pkcol = XML::LibXML::Element->new('column');
		$pkcol->setAttribute('name', 'history_id');
		$pkelt->appendChild($pkcol);

		my $change_types = {
			bigserial => "bigint",
			serial => "int"
		};

		my @hcols = (
		["history_id",'{ID_TYPE}'],
		["history_timestamp","timestamp"],
		["history_db_op","char(1)"],
		["history_deletes","bool"],
		["rev_id",'{IDREF_TYPE}'],
		);
		foreach my $col ($elt->getChildrenByTagName('column')) {
			my $type = $self->dbconfig->type_sub($col->getAttribute('type'));
			$type = $change_types->{$type} if(exists $change_types->{$type});
			push @hcols, [$col->getAttribute('name'),$type];
		}
		foreach my $col (@hcols) {
			my $c = XML::LibXML::Element->new('column');
			$htelt->appendChild($c);
			$c->setAttribute('name',$col->[0]);
			$c->setAttribute('type',$col->[1]);
		}
		my $cname = "c_zzh_" . $name. "_dbop";
		my $con = XML::LibXML::Element->new('constraint');
#		$con->setAttribute('id',$cname);
		$con->setAttribute('type', 'generic');
		$con->appendText("check (history_db_op in ('I','U','D'))");
		$htelt->appendChild($con);

		my $trig = XML::LibXML::Element->new("trigger");
		$trig->setAttribute('name',"history");
		$trig->setAttribute('when',"after insert or update or delete");
		$trig->setAttribute('each',"row");
		$trig->setAttribute('execute',"history_trigger");
		$elt->appendChild($trig);
	}

	return @elts;
}

=item B<gen_table_elt>

$elt = $self->gent_table_elt($info);

$info ={
	name=>"hcs",
	pk=>['id'],
	cols=>[["id",'{ID_TYPE}'],
	['parent','{IDREF_TYPE}'],
	['name','{OBJECT_NAME_TYPE}',{nullAllowed=>0}],
	['ordinal','bigint',{nullAllowed=>0}],
	['is_mp','boolean',{nullAllowed=>0}],
	["owner",'{OBJECT_NAME_TYPE}']],
	fks=>[{table=>'hcs',cols=>[['parent','id']]}],
	cons=>[{type=>'unique',cols=>['parent','ordinal']}],
	history=>1,
}

=cut

sub gen_table_elt {
	my $self = shift;
	my ($info) = @_;

	my $name = $info->{'name'};
	my $elt = XML::LibXML::Element->new("table");
	$elt->setAttribute("name",$name);
	my $pkelt = $elt->appendChild(
		XML::LibXML::Element->new("primaryKey")
	);
	foreach my $col (@{$info->{'pk'}}) {
		my $colelt = XML::LibXML::Element->new('column');
		$colelt->setAttribute('name',$col);
		$pkelt->appendChild($colelt);
	}
	foreach my $con (@{$info->{'fks'}}) {
		my $conelt = XML::LibXML::Element->new('constraint');
		$conelt->setAttribute('type','foreignKey');
		$conelt->setAttribute('refTable',$con->{table});
		my $fk = $elt->appendChild($conelt);
		my @colnames;
		foreach my $col (@{$con->{'cols'}}) {
			my $colelt = XML::LibXML::Element->new('column');
			$colelt->setAttribute('name',$col->[0]);
			$colelt->setAttribute('references',$col->[1]);
			$fk->appendChild($colelt);
			push @colnames, $col->[0];
		}
#		$fk->setAttribute('id',$self->con_name($name,"fk",@colnames));
	}
	foreach my $con (@{$info->{'cons'}}) {
		my $conelt = XML::LibXML::Element->new('constraint');
		$conelt->setAttribute('type',$con->{type});
		my $celt = $elt->appendChild($conelt);
    $celt->appendText($con->{text}) if exists $con->{text};
		foreach my $col (@{$con->{'cols'}}) {
			my $colelt = XML::LibXML::Element->new('column');
			$colelt->setAttribute('name',$col);
			$celt->appendChild($colelt);
		}
#		$celt->setAttribute
#			('id',$self->con_name($name,lc($con->{'type'}),@{$con->{'cols'}}));
	}
	foreach my $col (@{$info->{'cols'}}) {
		my $celt = XML::LibXML::Element->new('column');
		$elt->appendChild($celt);
		$celt->setAttribute('name',$col->[0]);
		$celt->setAttribute('type',$col->[1]);
		if(exists $col->[2]) {
			foreach my $att (keys %{$col->[2]}) {
				$celt->setAttribute($att,$col->[2]->{$att});
			}
		}
	}
	if(exists $info->{history}) {
		$elt->setAttribute('history',$info->{history});
	}

	return $self->mach_table_to_canonical($elt);
}

sub con_name {
	my $self = shift;

	my $sep = "_";
	my $cn = "c";
	foreach (@_) {
		$cn .= $sep;
		my $item = $_;
#	$item =~ s/objectsoftype_/objs_/g;
#	$item =~ s/hcattachments_/hcatt_/g;
#	$item =~ s/hccontents_/hccon_/g;
#	$item =~ s/setmembers_/setm_/g;
		$item =~ s/(_+)(.)/\u$2/g;
		$cn .= $item;
	}
	return $cn;
}


=back

=cut

1;
