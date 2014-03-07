Exec {
  path => ['/bin/', '/sbin/' , '/usr/bin/', '/usr/sbin/']
}

class configuration {
}

class system-update {
  Class['configuration'] -> Class['system-update']

  exec {'system-update.apt-get-update':
    user => 'root',
    command => 'apt-get update'
  }

  package {['python', 'python-virtualenv', 'curl']:
    ensure => present,
    require => Exec['system-update.apt-get-update'],
  }
}

class varnish {
  Class['system-update'] -> Class['varnish']

  exec {'varnish.add-apt-key':
    user => 'root',
    creates => '/home/vagrant/.vagrant.varnish.add-apt-key',
    command => 'curl http://repo.varnish-cache.org/debian/GPG-key.txt | apt-key add - && touch /home/vagrant/.vagrant.varnish.add-apt-key',
  }

  file {'/etc/apt/sources.list.d/varnish.list':
    ensure => present,
    mode => 0644,
    owner => 'root',
    group => 'root',
    source => '/vagrant/extras/vagrant/files/apt/varnish.list',
    require => Exec['varnish.add-apt-key'],
  }

  exec {'varnish.apt-get-update':
    user => 'root',
    command => 'apt-get update',
    require => File['/etc/apt/sources.list.d/varnish.list'],
  }

  package {'varnish':
    ensure => present,
    require => Exec['varnish.apt-get-update'],
  }

  service {'varnish':
    enable => true,
    ensure => running,
    require => Package['varnish'],
  }

  file {'/etc/varnish/default.vcl':
    ensure => present,
    mode => 0644,
    owner => 'root',
    group => 'root',
    source => '/vagrant/extras/vagrant/files/varnish/default.vcl',
    notify => Service['varnish'],
    require => Package['varnish'],
  }
}

class nginx {
  Class['system-update'] -> Class['nginx']

  package {'nginx':
    ensure => present,
  }

  service {'nginx':
    enable => true,
    ensure => running,
    require => Package['nginx'],
  }

  file {'/etc/nginx/sites-available/default':
    ensure => present,
    mode => 0644,
    owner => 'root',
    group => 'root',
    source => '/vagrant/extras/vagrant/files/nginx/default',
    notify => Service['nginx'],
    require => Package['nginx'],
  }
}

class virtualenv {
  Class['system-update'] -> Class['virtualenv']

  exec {'virtualenv.create':
    creates => '/home/vagrant/virtualenv/',
    user => 'vagrant',
    command => 'virtualenv /home/vagrant/virtualenv',
  }

  exec {'virtualenv.install-dependencies':
    user => 'vagrant',
    provider => 'shell',
    command => '. /home/vagrant/virtualenv/bin/activate && pip install -r /vagrant/requirements.txt',
    require => Exec['virtualenv.create'],
  }
}

class user {
  Class['system-update'] -> Class['user']

  exec {'user.force-color-prompt':
    user => 'vagrant',
    onlyif  => 'grep -c "^#force_color_prompt=yes" /home/vagrant/.bashrc',
    command => 'sed -i "s/^#force_color_prompt=yes/force_color_prompt=yes/" /home/vagrant/.bashrc',
  }

  file {'/home/vagrant/.profile':
    ensure => present,
    mode => 0644,
    owner => 'vagrant',
    group => 'vagrant',
    source => '/vagrant/extras/vagrant/files/user/profile',
  }
}

include configuration
include system-update
include varnish
include nginx
include virtualenv
include user
