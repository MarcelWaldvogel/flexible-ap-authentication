# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/bionic64"

  config.vm.network "forwarded_port", guest: 1812, host: 1812, protocol: "udp", host_ip: "0.0.0.0"

  # change file permissions in mounted /vagrant such that freeRADIUS can
  # access the python source files directly
  config.vm.synced_folder ".", "/vagrant", mount_options: ["fmode=0644"]

  config.vm.provision "ansible_local" do |ansible|
    ansible.playbook = "playbook.yml"
    ansible.install_mode = "pip" # workaround for ubuntu bionic
    ansible.provisioning_path = "/vagrant/config"
  end
end
