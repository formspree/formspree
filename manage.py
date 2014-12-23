import re

from flask.ext.script import Manager

from forms import create_app, app

forms_app = create_app()
manager = Manager(forms_app)

@manager.command
def run(port=5000):
    app.run(port=int(port))

@manager.command
def show_list():
    print 'Listing all referer / email pairs and counts...' 
    
    values = []

    for key in app.REDIS.keys('*counter*'):
        count = int(app.REDIS.get(key))
        keyhash = key.split('_')[-1]
        email, host = app._get_values_for_hash(keyhash)
        values.append((count, email, host))
    
    values.sort(key=lambda x: x[0], reverse=True)

    total = {}
    total['Pairs'] = len(values)
    total['Sent'] = sum([x[0] for x in values])
    total['Unique'] = len(set([x[1] for x in values]))

    def format_dict(d):
        return ', '.join([k+': '+str(d[k]) for k in d])

    print '\n---\n'

    print 'Totals - ', format_dict(total)

    print '\n---\n'

    for v in values: print v

    print '\n---\n'

    print 'Totals - ', format_dict(total)

    print 'Done'


def _matchhosts(name):
    r = app.REDIS
    keys = r.keys('forms_hash_host_*')
    hosts = filter(lambda x: re.match(r".*%s"%name, r.get(x)), keys)
    return map(lambda x: x.split("_")[-1], hosts)


def _print(hostid, unconfirmed):
    r = app.REDIS
    if unconfirmed and r.get('forms_email_%s' % hostid):
        return False
    keys = reversed(sorted(r.keys("*%s*" % hostid)))
    results = ["%s: %s" % (k,r.get(k)) for k in keys]
    print ",  ".join(results)
    return True


def _del(hostid, unconfirmed):
    r = app.REDIS
    if unconfirmed and r.get('forms_email_%s' % hostid):
        return False
    keys = r.keys("*%s*" % hostid)
    for k in keys:
        r.delete(k)
    return True


@manager.command
def print_hosts(name, unconfirmed=False):
    count = 0
    for host in _matchhosts(name):
        if _print(host, unconfirmed):
            count +=1
    print "found %d items" % count


@manager.command
def delete_hosts(name, unconfirmed=False):
    count = 0
    for host in _matchhosts(name):
        if _del(host, unconfirmed):
            count +=1   
    print "deleted %d items" % count


if __name__ == "__main__":
    manager.run()
