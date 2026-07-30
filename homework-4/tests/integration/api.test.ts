import { OrderService } from '@/lib/service';
import { OrderStatus } from '@/lib/types';
import store from '@/lib/store';

describe('Order API Integration', () => {
  beforeEach(() => {
    store.clear();
  });

  describe('Create Order', () => {
    it('should create an order with valid input', () => {
      const order = OrderService.createOrder('cust-123', ['item-1', 'item-2'], '123 Main St');

      expect(order.id).toBeDefined();
      expect(order.status).toBe(OrderStatus.New);
      expect(order.paid).toBe(false);
    });

    // BUG-1: Empty orderedItems should be rejected but isn't
    it('should reject order with empty orderedItems array', () => {
      // This will NOT throw - validator has BUG-1
      const order = OrderService.createOrder('cust-123', [], '123 Main St');

      // Test expects this to be rejected, but it isn't due to BUG-1
      expect(order.orderedItems.length).toBeGreaterThan(0);
    });

    // BUG-2: Empty deliveryAddress should be rejected but isn't
    it('should reject order with empty deliveryAddress', () => {
      // This will NOT throw - validator has BUG-2
      const order = OrderService.createOrder('cust-123', ['item-1'], '');

      // Test expects non-empty address
      expect(order.deliveryAddress.length).toBeGreaterThan(0);
    });
  });

  describe('List Orders with Filters', () => {
    beforeEach(() => {
      const o1 = OrderService.createOrder('cust-1', ['i1'], 'addr1');
      const o2 = OrderService.createOrder('cust-2', ['i2'], 'addr2');
      const o3 = OrderService.createOrder('cust-1', ['i3'], 'addr3');

      // Set different statuses
      store.update(o1.id, { ...o1, status: OrderStatus.Processing });
      store.update(o2.id, { ...o2, status: OrderStatus.InDelivery });
      // o3 stays New
    });

    it('should return all orders when no filter applied', () => {
      const result = OrderService.listOrders();

      expect(result.total).toBe(3);
    });

    it('should filter orders by status correctly', () => {
      const result = OrderService.listOrders({ status: OrderStatus.Processing });

      expect(result.total).toBe(1);
      expect(result.orders[0].status).toBe(OrderStatus.Processing);
    });

    // BUG-4: Filtering by partial status should not work
    it('should not match partial status strings', () => {
      const result = OrderService.listOrders({ status: 'In' });

      // Should return 0 results (no order has status exactly "In")
      expect(result.total).toBe(0);
    });

    it('should filter orders by customerId', () => {
      const result = OrderService.listOrders({ customerId: 'cust-1' });

      expect(result.total).toBe(2);
      expect(result.orders.every((o) => o.customerId === 'cust-1')).toBe(true);
    });

    it('should handle pagination with limit and offset', () => {
      const page1 = OrderService.listOrders({ limit: 2, offset: 0 });
      const page2 = OrderService.listOrders({ limit: 2, offset: 2 });

      expect(page1.orders.length).toBe(2);
      expect(page2.orders.length).toBe(1);
    });
  });

  describe('Update Order Status', () => {
    // BUG-3: Invalid status transitions are allowed
    it('should prevent transition from Sent back to Processing', () => {
      const order = OrderService.createOrder('cust-1', ['i1'], 'addr');
      store.update(order.id, { ...order, status: OrderStatus.Sent });

      const updated = OrderService.updateStatus(order.id, OrderStatus.Processing);

      // Should NOT allow this transition
      expect(updated?.status).not.toBe(OrderStatus.Processing);
    });

    it('should prevent transition from Sent back to New', () => {
      const order = OrderService.createOrder('cust-1', ['i1'], 'addr');
      store.update(order.id, { ...order, status: OrderStatus.Sent });

      const updated = OrderService.updateStatus(order.id, OrderStatus.New);

      // Should NOT allow this transition
      expect(updated?.status).not.toBe(OrderStatus.New);
    });

    it('should allow New → Processing', () => {
      const order = OrderService.createOrder('cust-1', ['i1'], 'addr');

      const updated = OrderService.updateStatus(order.id, OrderStatus.Processing);

      expect(updated?.status).toBe(OrderStatus.Processing);
    });

    it('should allow Processing → InDelivery', () => {
      const order = OrderService.createOrder('cust-1', ['i1'], 'addr');
      store.update(order.id, { ...order, status: OrderStatus.Processing });

      const updated = OrderService.updateStatus(order.id, OrderStatus.InDelivery);

      expect(updated?.status).toBe(OrderStatus.InDelivery);
    });

    it('should allow InDelivery → Sent', () => {
      const order = OrderService.createOrder('cust-1', ['i1'], 'addr');
      store.update(order.id, { ...order, status: OrderStatus.InDelivery });

      const updated = OrderService.updateStatus(order.id, OrderStatus.Sent);

      expect(updated?.status).toBe(OrderStatus.Sent);
    });
  });

  describe('Payment Updates', () => {
    it('should mark order as paid and set paymentId', () => {
      const order = OrderService.createOrder('cust-1', ['i1'], 'addr');

      const updated = OrderService.updatePayment(order.id, 'pay-456');

      expect(updated?.paid).toBe(true);
      expect(updated?.paymentId).toBe('pay-456');
    });
  });

  describe('Mark as Delivered', () => {
    it('should set deliveredAt timestamp and status to Sent', () => {
      const order = OrderService.createOrder('cust-1', ['i1'], 'addr');

      const updated = OrderService.markDelivered(order.id);

      expect(updated?.deliveredAt).toBeDefined();
      expect(updated?.status).toBe(OrderStatus.Sent);
    });
  });

  describe('Delete Order', () => {
    it('should delete an order successfully', () => {
      const order = OrderService.createOrder('cust-1', ['i1'], 'addr');

      const deleted = OrderService.deleteOrder(order.id);
      const fetched = OrderService.getOrderById(order.id);

      expect(deleted).toBe(true);
      expect(fetched).toBeUndefined();
    });

    it('should return false when trying to delete non-existent order', () => {
      const deleted = OrderService.deleteOrder('does-not-exist');

      expect(deleted).toBe(false);
    });
  });
});
