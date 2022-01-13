# IMPORTANT: when an update is needed, run
#
# docker login github-registry.cern.ch
# docker build -t github.com/donpablonow/lb-workspace-template/centos7-build:v4.57.py3 .
# docker push github.com/donpablonow/lb-workspace-template/centos7-build:v4.57.py3
# docker logout github-registry.cern.ch

# image should match what is used for lb-docker-run (see build-env)
FROM github-registry.cern.ch/lhcb-core/lbdocker/centos7-build:v4.57

RUN sudo yum install -y python3 \
    && sudo yum clean all && sudo rm -rf /var/cache/yum
