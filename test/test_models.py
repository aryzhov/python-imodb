import imodb


class Customer(imodb.Model):
    id = imodb.Field(is_key=True)
    name = imodb.Field(default='Anonymous')
    orders = imodb.CollectionField(ref_model='Order', reverse_ref='customer')


class Order(imodb.Model):
    id = imodb.Field(is_key=True)
    amount = imodb.Field()
    customer = imodb.ReferenceField(ref_model=Customer, reverse_ref='orders')


class Order2(Order):
    company = imodb.Field()


def test_simple_fields():
    cust = Customer(id=1)
    assert cust.id == 1
    assert cust.name == 'Anonymous'
    p1 = Order(id=1, desc='Project1')
    assert p1.id == 1
    assert p1.desc == 'Project1'


def test_refs():
    cust = Customer(id=1, name='Customer1')
    o1 = Order(id=1, amount=10, customer=cust)
    assert dict(cust.orders) == {1: o1}
    o2 = Order2(id=2, amount=20, company='Company1')
    cust.orders += o2
    assert dict(cust.orders) == {1: o1, 2: o2}
    cust.orders -= o1
    assert dict(cust.orders) == {2: o2}
    assert o1.customer is None


def test_update():
    cust = Customer(id=1, desc='Org1')
    o = Order(id=1, amount=10, customer=cust)
    assert 1 in cust.orders and cust.orders[1] is o
    o2 = Order(id=2, amount=20)
    o.update(o2)
    assert o.customer == cust
    assert dict(cust.orders) == {2: o}
