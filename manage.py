import re

from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand

from forms import app

forms_app = app.app
manager = Manager(forms_app)


# add flask-migrate commands
Migrate(forms_app, app.DB)
manager.add_command('db', MigrateCommand)

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


@manager.command
def redis_to_postgres():
    import redis
    from forms.settings import REDIS_URL
    from forms.app import DB, Form, HASH
    r = redis.Redis.from_url(REDIS_URL)

    hashes = set()
    for k in r.keys():
        keyparts = k.split('_')
        if keyparts[0] == 'forms':
            hashes.add(keyparts[-1])

    print "found %s different hashes" % len(hashes)

    print "creating tables"
    DB.create_all(app=forms_app)

    print "building form rows"
    for hash in hashes:
        email = r.get('forms_hash_email_%s' % hash)
        host = r.get('forms_hash_host_%s' % hash)
        confirm_sent = bool(r.get('forms_nonce_%s' % hash))
        confirmed = bool(r.get('forms_email_%s' % hash))
        counter = r.get('forms_counter_%s' % hash) or 0

        form = Form.query.filter_by(hash=HASH(email, host)).first() or Form(email, host)
        form.confirm_sent = confirm_sent
        form.counter = counter
        form.confirmed = confirmed
        form.counter = counter
        DB.session.add(form)

    print "commiting to the database"
    DB.session.commit()


if __name__ == "__main__":
    manager.run()
