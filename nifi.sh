# Nifi Installation

# CONFIGURATION
KEYSTORE_PASSWD="ecef4f07452e4181df757926157dc54fda7883aa"
TRUSTSTORE_PASSWD="77d9f442049bf7727b864f957b7b064ffef2d5a6"

CLUSTER_MODE=false

# LDAP CONFIGURATION (TODO: USE LDAPS)
LDAP_MODE="SIMPLE"
LDAP_URIS="ldap://aiqawsdc-mmdo690.aiq.local ldap://aiqawsdc-8vt2tcq.aiq.local"
LDAP_BIND_DN="CN=NiFi Prod,OU=Service Accounts,DC=aiq,DC=local"
LDAP_BIND_PASSWD="52bd6c41-d785-4266-bb82-ba1b9130d164"
LDAP_BASE_DN="DC=aiq,DC=local"
LDAP_FILTER="sAMAccountName={0}"
# note: can't use LDAPS yet as the DC's CA is not in the truststore

# POST-LAUNCH Authorization Configuration
# Once nifi is online, you will need to manually grant access to the main process group to the predefined users. Right-click the main canvas and "Manage access policies".
# view the component: Viewers, Editors, Operators, and Admins
# modify the component: Editors and Admins
# operate the component: Operators, Editors and Admins
# view provenance: Viewers, Editors, Operators and Admins
# view the data: Editors, Operators, and Admins
# modify the data: Editors, Admins
# view the policies: Viewers, Editors, Operators, and Admins
# modify the policies: Admins

# special note:
#  LDAP is configured for AUTHENTICATION, but not AUTHORIZATION
#  The Administrator user is created as super-user. You will need to add
#  any users you want to have access manually. This was supposedly enhanced
#  with nifi 1.4, but I could not figure out the ldap authorizer.

if [[ -z "$KEYSTORE_PASSWD" ]]; then
  read -e -s -p "Enter keystore password: " KEYSTORE_PASSWD
  echo
fi

if [[ -z "$TRUSTSTORE_PASSWD" ]]; then
  read -e -s -p "Enter truststore password: " TRUSTSTORE_PASSWD
  echo
fi


# pre-requisites
apt-get update -y ; apt-get upgrade -y
apt-get install -y openjdk-11-jdk-headless openjdk-11-jre-headless

#### DOWNLOAD AND INSTALL
# download nifi itself
cd /opt
wget https://archive.apache.org/dist/nifi/1.17.0/nifi-1.17.0-bin.zip 
unzip nifi-1.17.0-bin.zip
# wget https://archive.apache.org/dist/nifi/1.14.0/nifi-1.14.0-bin.tar.gz
# tar xzf nifi-1.14.0-bin.tar.gz
ln -s nifi-1.14.0 nifi

# download and install nifi toolkit
cd /opt
wget https://archive.apache.org/dist/nifi/1.17.0/nifi-toolkit-1.17.0-bin.zip  
unzip nifi-toolkit-1.17.0-bin.zip  
# wget https://archive.apache.org/dist/nifi/1.14.0/nifi-toolkit-1.14.0-bin.tar.gz
# tar xzf nifi-toolkit-1.14.0-bin.tar.gz
ln -s nifi-toolkit-1.14.0 nifi-toolkit

# (re)set file permissions
for dir in /opt/nifi /opt/nifi-toolkit; do
  chmod -R o+r $dir
  chmod -R o+rx $dir/bin
  find $dir -type d -follow | xargs chmod o+rx
done

#### SYSTEM CONFIGURATION

# set sysctls per admin guide
cat > /etc/security/limits.d/50-nifi.conf << EOM
# maximum file handles
* hard nofile 50000
* soft nofile 50000

# maximum forked processes
* hard nproc 10000
* soft nproc 10000
EOM

cat > /etc/sysctl.d/50-nifi.conf << EOM
net.ipv4.ip_local_port_range = "10000 65000"
net.ipv4.netfilter.ip_conntrack_tcp_timeout_time_wait = 1
net.netfilter.nf_conntrack_tcp_timeout_time_wait = 1
vm.swappiness = 0
EOM


#### NIFI CONFIGURATION

# create user (with shell)
useradd -d /opt/nifi -s /bin/bash nifi

# create directories for nifi data
for dir in \
  /var/db/nifi/database_repository \
  /var/db/nifi/flowfile_repository \
  /var/db/nifi/provenance_repository \
  /var/db/nifi/flow \
  /var/db/nifi/work/jetty \
  /var/db/nifi/ \
  /data/nifi/content_repository \
  /data/nifi/tmp \
  /data/nifi/work \
  /data/nifi \
  /data/nifi/templates \
  /var/log/nifi \
  /var/run/nifi;
do
  mkdir -p $dir
  chown -R nifi $dir
done

# open up permissions a bit "chmod 755" would be appropriate
# use semantic instead; add permission without specifically setting them
# owner, group, other
# already done in bootstrap-debian.sh
# chmod go=rx /var/log

# create a sy
# these directories CANNOT be configured around; use a symlink
ln -s /var/run/nifi /opt/nifi/run
ln -s /var/log/nifi /opt/nifi/logs

# configure the boostrap to point java.io.tmpdir to /data/nifi/tmp
sed -i '/java.arg.99=/d' conf/bootstrap.conf
echo "java.arg.99=-Djava.io.tmpdir=/data/nifi/tmp" >> conf/bootstrap.conf

# configure nifi. use crudini to make some of this easier
test -e conf/nifi.properties.orig || cp conf/nifi.properties conf/nifi.properties.orig
apt-get install crudini -y

# older versions of nifi use an xml representation of the flow; required for backwards compatibility!
alias conf='crudini --set conf/nifi.properties "" '
conf nifi.flow.configuration.file /var/db/nifi/flow/flow.xml.gz
# newer versions of nifi use a json representation of the flow; needed in version 1.17
conf nifi.flow.configuration.json.file /var/db/nifi/flow/flow.json.gz

# enable dataflow archiving
conf nifi.flow.configuration.archive.enabled true
conf nifi.flow.configuration.archive.dir /var/db/nifi/flow/archive
conf nifi.flow.configuration.archive.max.time "120 days"
conf nifi.flow.configuration.archive.max.storage "500 MB"
conf nifi.flow.configuration.archive.max.count ""

# keep most processors from hammering the system with a backoff when bored
conf nifi.bored.yield.duration "250 millis"

# config authorizers and identity providers
conf nifi.authorizer.configuration.file ./conf/authorizers.xml
conf nifi.login.identity.provider.configuration.file ./conf/login-identity-providers.xml

# move temp/work stuff out of /opt
conf nifi.templates.directory /data/nifi/templates
conf nifi.nar.working.directory /data/nifi/work/nar/
conf nifi.documentation.working.directory /data/nifi/work/docs/components

# state management; use the zk provider
conf nifi.state.management.configuration.file  ./conf/state-management.xml
conf nifi.state.management.provider.local local-provider
conf nifi.state.management.provider.cluster zk-provider
conf nifi.state.management.embedded.zookeeper.start false

# cluster configuration
conf nifi.cluster.is.node ${CLUSTER_MODE}
conf nifi.cluster.node.address $(hostname --fqdn)
conf nifi.cluster.node.protocol.port 3121
conf nifi.cluster.protocol.is.secure true

# h2 database_repository
conf nifi.database.directory /var/db/nifi/database_repository

# flowfile repo
conf nifi.flowfile.repository.directory /var/db/nifi/flowfile_repository

# content repo (hdfs in future?)
conf nifi.content.repository.implementation org.apache.nifi.controller.repository.FileSystemRepository
conf nifi.content.repository.directory.default /data/nifi/content_repository
conf nifi.content.repository.archive.enabled true
conf nifi.content.repository.archive.max.retention.period "21 days"
conf nifi.content.repository.archive.max.usage.percentage "50%"

# provenance repository
conf nifi.provenance.repository.directory.default /var/db/nifi/provenance_repository
conf nifi.provenance.repository.max.storage.time "90 days"
conf nifi.provenance.repository.max.storage.size "4 GB"
conf nifi.provenance.repository.rollover.time "10 mins"
conf nifi.provenance.repository.rollover.size "100 MB"

# jetty config
conf nifi.web.https.host localhost
conf nifi.web.https.port 8443
conf nifi.web.jetty.working.directory /var/db/nifi/work/jetty

# initialize and configure tls
mkdir -p /var/db/nifi/secure
chown nifi /var/db/nifi/secure
chmod 700 /var/db/nifi/secure

# make sure nifi has permission to do stuff in /var/db
chmod ugo+rx /var/db

# generate the truststore, keystore
if [[ ! -e "/var/db/nifi/secure/nifi-key.key" ]]; then
  ( cd /opt/nifi-toolkit ; sudo -u nifi \
    bin/tls-toolkit.sh standalone \
	  -o /var/db/nifi/secure \
	  -n $(hostname --fqdn) \
	  --keyPassword "${KEYSTORE_PASSWD}" \
	  --keyStorePassword "${KEYSTORE_PASSWD}" \
	  --trustStorePassword "${TRUSTSTORE_PASSWD}" \
  )
fi

conf nifi.security.keystore /var/db/nifi/secure/$(hostname --fqdn)/keystore.jks
conf nifi.security.keystoreType jks
conf nifi.security.keystorePasswd "${KEYSTORE_PASSWD}"
conf nifi.security.keyPasswd "${KEYSTORE_PASSWD}"
conf nifi.security.truststore /var/db/nifi/secure/$(hostname --fqdn)/truststore.jks
conf nifi.security.truststoreType jks
conf nifi.security.truststorePasswd "${TRUSTSTORE_PASSWD}"

# use the keystore pass to encrypt sensitive props
conf nifi.sensitive.props.key "$KEYSTORE_PASSWD"


# configure ldap
conf nifi.security.user.login.identity.provider ldap-provider
conf nifi.security.user.authorizer managed-authorizer

# zookeeper
conf nifi.zookeeper.connect.string localhost:2181
conf nifi.zookeeper.root.node /nifi

# configure identity providers

# configure zk state
test -e conf/state-management.xml.orig || cp conf/state-management.xml conf/state-management.xml.orig
cat > conf/state-management.xml << 'EOM'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<stateManagement>
    <!-- although unused in clustered mode, local provider is required. this is ultimately ignored -->
    <local-provider>
        <id>local-provider</id>
        <class>org.apache.nifi.controller.state.providers.local.WriteAheadLocalStateProvider</class>
        <property name="Directory">/var/db/nifi/state</property>
        <property name="Always Sync">false</property>
        <property name="Partitions">16</property>
        <property name="Checkpoint Interval">2 mins</property>
    </local-provider>

    <cluster-provider>
        <id>zk-provider</id>
        <class>org.apache.nifi.controller.state.providers.zookeeper.ZooKeeperStateProvider</class>
        <property name="Connect String">localhost:2181</property>
        <property name="Root Node">/nifi</property>
        <property name="Session Timeout">10 seconds</property>
        <property name="Access Control">Open</property>
    </cluster-provider>
	
</stateManagement>
EOM

# configure LDAP for AUTHENTICATION.
test -e conf/login-identity-providers.xml.orig || cp conf/login-identity-providers.xml conf/login-identity-providers.xml.orig
cat > conf/login-identity-providers.xml << EOM
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<loginIdentityProviders>
    <provider>
        <identifier>ldap-provider</identifier>
        <class>org.apache.nifi.ldap.LdapProvider</class>
        <property name="Authentication Strategy">${LDAP_MODE}</property>

        <property name="Manager DN">${LDAP_BIND_DN}</property>
        <property name="Manager Password">${LDAP_BIND_PASSWD}</property>

        <property name="Referral Strategy">FOLLOW</property>
        <property name="Connect Timeout">10 secs</property>
        <property name="Read Timeout">10 secs</property>

        <property name="Url">${LDAP_URIS}</property>
        <property name="User Search Base">${LDAP_BASE_DN}</property>
        <property name="User Search Filter">${LDAP_FILTER}</property>

        <property name="Identity Strategy">USE_USERNAME</property>
        <property name="Authentication Expiration">12 hours</property>
    </provider>
</loginIdentityProviders>
EOM

# use local files for AUTHORIZATION.
test -e conf/authorizers.xml.orig || cp conf/authorizers.xml conf/authorizers.xml.orig
cat > conf/authorizers.xml << EOM
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<authorizers>
    <userGroupProvider>
        <identifier>file-user-group-provider</identifier>
        <class>org.apache.nifi.authorization.FileUserGroupProvider</class>
        <property name="Users File">/var/db/nifi/access/users.xml</property>
        <property name="Legacy Authorized Users File"></property>
        <property name="Initial User Identity 1">Administrator</property>
    </userGroupProvider>

    <accessPolicyProvider>
        <identifier>file-access-policy-provider</identifier>
        <class>org.apache.nifi.authorization.FileAccessPolicyProvider</class>
        <property name="User Group Provider">file-user-group-provider</property>
        <property name="Authorizations File">/var/db/nifi/access/authorizations.xml</property>
        <property name="Initial Admin Identity">Administrator</property>
        <property name="Legacy Authorized Users File"></property>
        <property name="Node Identity 1"></property>
        <property name="Node Group"></property>
    </accessPolicyProvider>

    <authorizer>
        <identifier>managed-authorizer</identifier>
        <class>org.apache.nifi.authorization.StandardManagedAuthorizer</class>
        <property name="Access Policy Provider">file-access-policy-provider</property>
    </authorizer>

</authorizers>
EOM

# configure some default groups and policies
mkdir -p /var/db/nifi/access
chown -R nifi /var/db/nifi/access

if [[ ! -e /var/db/nifi/access/users.xml ]]; then
VIEWER_UUID=$( uuidgen )
EDITOR_UUID=$( uuidgen )
OPERATOR_UUID=$( uuidgen )
ADMIN_UUID=$( uuidgen )
ADMINISTRATOR_UUID=$( uuidgen )

cat > /var/db/nifi/access/users.xml << EOM
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<tenants>
    <groups>
        <group identifier="${VIEWER_UUID}" name="Viewers"/>
        <group identifier="${EDITOR_UUID}" name="Editors"/>
        <group identifier="${OPERATOR_UUID}" name="Operators"/>
        <group identifier="${ADMIN_UUID}" name="Administrators">
            <user identifier="${ADMINISTRATOR_UUID}"/>
        </group>
    </groups>
    <users>
        <user identifier="${ADMINISTRATOR_UUID}" identity="Administrator"/>
    </users>
</tenants>
EOM

cat > /var/db/nifi/access/authorizations.xml << EOM
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<authorizations>
    <policies>
        <policy identifier="$( uuidgen )" resource="/flow" action="R">
            <group identifier="${VIEWER_UUID}"/>
            <group identifier="${EDITOR_UUID}"/>
            <group identifier="${OPERATOR_UUID}"/>
            <group identifier="${ADMIN_UUID}"/>
        </policy>
        <policy identifier="$( uuidgen )" resource="/flow" action="W">
            <group identifier="${EDITOR_UUID}"/>
            <group identifier="${ADMIN_UUID}"/>
        </policy>

        <policy identifier="$( uuidgen )" resource="/data" action="R">
            <group identifier="${VIEWER_UUID}"/>
            <group identifier="${EDITOR_UUID}"/>
            <group identifier="${OPERATOR_UUID}"/>
            <group identifier="${ADMIN_UUID}"/>
        </policy>
        <policy identifier="$( uuidgen )" resource="/data" action="W">
            <group identifier="${ADMIN_UUID}"/>
        </policy>

       <policy identifier="$( uuidgen )" resource="/controller" action="R">
            <group identifier="${VIEWER_UUID}"/>
            <group identifier="${EDITOR_UUID}"/>
            <group identifier="${OPERATOR_UUID}"/>
            <group identifier="${ADMIN_UUID}"/>
        </policy>
        <policy identifier="$( uuidgen )" resource="/controller" action="W">
            <group identifier="${EDITOR_UUID}"/>
            <group identifier="${OPERATOR_UUID}"/>
            <group identifier="${ADMIN_UUID}"/>
        </policy>
        
        <policy identifier="$( uuidgen )" resource="/provenance" action="R">
           <group identifier="${VIEWER_UUID}"/>
           <group identifier="${EDITOR_UUID}"/>
           <group identifier="${OPERATOR_UUID}"/>
           <group identifier="${ADMIN_UUID}"/>
        </policy>

        <policy identifier="$( uuidgen )" resource="/counters" action="R">
           <group identifier="${VIEWER_UUID}"/>
           <group identifier="${EDITOR_UUID}"/>
           <group identifier="${OPERATOR_UUID}"/>
           <group identifier="${ADMIN_UUID}"/>
        </policy>


        <!-- admin-only policies -->
        <policy identifier="$( uuidgen )" resource="/tenants" action="R">
           <group identifier="${VIEWER_UUID}"/>
           <group identifier="${EDITOR_UUID}"/>
           <group identifier="${OPERATOR_UUID}"/>
            <group identifier="${ADMIN_UUID}"/>
        </policy>
        <policy identifier="$( uuidgen )" resource="/tenants" action="W">
            <group identifier="${ADMIN_UUID}"/>
        </policy>
        <policy identifier="$( uuidgen )" resource="/policies" action="R">
            <group identifier="${ADMIN_UUID}"/>
        </policy>
        <policy identifier="$( uuidgen )" resource="/policies" action="W">
            <group identifier="${ADMIN_UUID}"/>
        </policy>
        <policy identifier="$( uuidgen )" resource="/restricted-components" action="R">
            <group identifier="${ADMIN_UUID}"/>
        </policy>
        <policy identifier="$( uuidgen )" resource="/restricted-components" action="W">
            <group identifier="${ADMIN_UUID}"/>
        </policy>
    </policies>
</authorizations>
EOM
fi


#### SERVICE Installation
cat > /lib/systemd/system/nifi.service << 'EOM'
[Unit]
Description=Apache NiFi Server
After=network.target auditd.service

[Service]
Type=Simple
ExecStartPre=!mkdir -p /var/run/nifi ; !chown nifi /var/run/nifi
ExecStart=/opt/nifi/bin/nifi.sh run
User=nifi

[Install]
WantedBy=multi-user.target
EOM

systemctl daemon-reload

# start the service
systemctl enable nifi
systemctl start nifi


# SEE NEXT: it-nginx-reverse-proxy.sh
