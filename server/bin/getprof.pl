#!/usr/bin/perl
use Machination::WebClient;
use Machination::XMLConstructor;
use Machination::ConfigFile;
use Machination::Log;
use Getopt::Long;
use Data::Dumper;

$Data::Dumper::Indent=1;

my $config = "/home/eggy/svn/machination/trunk/test/machination/config.xml";
my $service_url = "http://localhost/machination/hierarchy/";
my $user = "os:testxp";
GetOptions(
           "config=s" => \$config,
           "service_url=s"=>\$service_url,
           "user=s"=>\$user,
          );
my $object = shift @ARGV;
my $conf_obj = Machination::ConfigFile->new($config);
my $log = Machination::Log->new;
my $log_elt = ($conf_obj->doc->
               getElementById("subconfig.haccess")->findnodes("log"))[0];
$log_elt->appendTextChild("logFile",
                          $conf_obj->get_file("file.haccess.LOG"));
$log->from_xml($log_elt);

$log->lmsg("getprof","getting profile for $object from $service_url",1);
my $wc = Machination::WebClient->new(url=>$service_url,user=>$user,
                                    log=>$log);

#my $ass = $wc->call("GetAssertionList",$object,2);

my $ass = do 'data.pl';

#print Dumper($ass);

my $con = Machination::XMLConstructor->new($wc);
#print Dumper($con->order_assertion_list($ass));
#$con->doc->documentElement->appendChild(XML::LibXML::Element->new("splat"));
#$con->doc->documentElement->addNewChild(undef,"prof");

my ($doc,$results) = $con->compile($ass);
print $con->doc->toString(1) . "\n";
foreach my $r (keys %$results) {
  print "$r: " . $results->{$r}->{ass_op} . " " .
    $results->{$r}->{ass_arg} . "\n";
}
