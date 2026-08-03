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

    // BUG-1: Empty orderedItems should be rejected
    it('should reject order with empty orderedItems array', () => {
      // Should throw when attempting to create order with empty items
      expect(() => {
        OrderService.createOrder('cust-123', [], '123 Main St');
      }).toThrow();
    });

    // BUG-2: Empty deliveryAddress should be rejected
    it('should reject order with empty deliveryAddress', () => {
      // Should throw when attempting to create order with empty address
      expect(() => {
        OrderService.createOrder('cust-123', ['item-1'], '');
      }).toThrow();
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

  describe('End-to-End Validation Flow - FIRST Principles Coverage', () => {
    describe('Happy Path - Complete Order Lifecycle', () => {
      it('should complete full order lifecycle: create → process → deliver → mark sent', () => {
        // Create order with valid data
        const created = OrderService.createOrder('cust-1', ['widget-1', 'widget-2'], '42 Main St');
        expect(created.status).toBe(OrderStatus.New);
        expect(created.paid).toBe(false);

        // Process the order
        const processed = OrderService.updateStatus(created.id, OrderStatus.Processing);
        expect(processed?.status).toBe(OrderStatus.Processing);

        // Move to delivery
        const inDelivery = OrderService.updateStatus(created.id, OrderStatus.InDelivery);
        expect(inDelivery?.status).toBe(OrderStatus.InDelivery);

        // Mark as delivered (sets to Sent)
        const delivered = OrderService.markDelivered(created.id);
        expect(delivered?.status).toBe(OrderStatus.Sent);
        expect(delivered?.deliveredAt).toBeDefined();

        // Verify order is in final state
        const final = OrderService.getOrderById(created.id);
        expect(final?.status).toBe(OrderStatus.Sent);
      });

      it('should handle payment updates during order lifecycle', () => {
        const order = OrderService.createOrder('cust-1', ['item-1'], 'addr1');
        expect(order.paid).toBe(false);

        const paid = OrderService.updatePayment(order.id, 'pay-789');
        expect(paid?.paid).toBe(true);
        expect(paid?.paymentId).toBe('pay-789');

        // Verify status can still be updated while order is paid
        const updated = OrderService.updateStatus(order.id, OrderStatus.Processing);
        expect(updated?.status).toBe(OrderStatus.Processing);
        expect(updated?.paid).toBe(true);
      });
    });

    describe('Error Path - Validation Rejection', () => {
      it('should reject order creation with empty orderedItems and throw', () => {
        expect(() => {
          OrderService.createOrder('cust-1', [], 'addr1');
        }).toThrow();
      });

      it('should reject order creation with empty deliveryAddress and throw', () => {
        expect(() => {
          OrderService.createOrder('cust-1', ['item-1'], '');
        }).toThrow();
      });

      it('should reject order creation with empty customerId and throw', () => {
        expect(() => {
          OrderService.createOrder('', ['item-1'], 'addr1');
        }).toThrow();
      });

      it('should provide specific error details in error message', () => {
        try {
          OrderService.createOrder('cust-1', [], '');
        } catch (error) {
          const message = (error as Error).message;
          const errors = JSON.parse(message);
          expect(errors).toHaveProperty('orderedItems');
          expect(errors).toHaveProperty('deliveryAddress');
        }
      });
    });

    describe('Edge Case - Boundary Conditions', () => {
      it('should create order with single item', () => {
        const order = OrderService.createOrder('cust-1', ['single-item'], 'addr1');
        expect(order.orderedItems).toEqual(['single-item']);
        expect(order.orderedItems.length).toBe(1);
      });

      it('should create order with many items', () => {
        const items = Array.from({ length: 100 }, (_, i) => `item-${i}`);
        const order = OrderService.createOrder('cust-1', items, 'addr1');
        expect(order.orderedItems.length).toBe(100);
      });

      it('should create order with minimal valid customerId', () => {
        const order = OrderService.createOrder('X', ['item-1'], 'addr1');
        expect(order.customerId).toBe('X');
      });

      it('should create order with minimal valid deliveryAddress', () => {
        const order = OrderService.createOrder('cust-1', ['item-1'], 'A');
        expect(order.deliveryAddress).toBe('A');
      });

      it('should handle special characters in customerId', () => {
        const order = OrderService.createOrder('CUST-2024-001-ABC', ['item'], 'addr');
        expect(order.customerId).toBe('CUST-2024-001-ABC');
      });

      it('should handle complex addresses with special characters', () => {
        const complexAddr = '123 O\'Brien St, Suite #200, Apt. 5, New York, NY 10001-1234';
        const order = OrderService.createOrder('cust-1', ['item'], complexAddr);
        expect(order.deliveryAddress).toBe(complexAddr);
      });

      it('should handle orderedItems with special characters', () => {
        const items = ['item-1', 'product/category', 'SKU#12345', 'Type: Premium'];
        const order = OrderService.createOrder('cust-1', items, 'addr1');
        expect(order.orderedItems).toEqual(items);
      });
    });

    describe('State Machine - Invalid Transition Enforcement', () => {
      it('should persist order state when invalid transition attempted', () => {
        const order = OrderService.createOrder('cust-1', ['item-1'], 'addr1');
        store.update(order.id, { ...order, status: OrderStatus.Sent });

        // Attempt invalid transition
        const attempted = OrderService.updateStatus(order.id, OrderStatus.Processing);

        // State must not change
        expect(attempted?.status).toBe(OrderStatus.Sent);

        // Verify store also reflects correct state
        const stored = OrderService.getOrderById(order.id);
        expect(stored?.status).toBe(OrderStatus.Sent);
      });

      it('should allow updateOrder to update fields independently of invalid status', () => {
        const order = OrderService.createOrder('cust-1', ['item-1'], 'old-address');
        store.update(order.id, { ...order, status: OrderStatus.Sent });

        const updated = OrderService.updateOrder(order.id, {
          status: OrderStatus.New,
          deliveryAddress: 'new-address',
        });

        // Status should not change (invalid transition rejected)
        expect(updated?.status).toBe(OrderStatus.Sent);
        // But other fields should update
        expect(updated?.deliveryAddress).toBe('new-address');
      });
    });

    describe('Filtering Behavior - Type Safety', () => {
      beforeEach(() => {
        OrderService.createOrder('cust-a', ['i1'], 'addr1');
        OrderService.createOrder('cust-b', ['i2'], 'addr2');
        OrderService.createOrder('cust-a', ['i3'], 'addr3');

        const orders = store.getAll();
        store.update(orders[0].id, { ...orders[0], status: OrderStatus.Processing });
        store.update(orders[1].id, { ...orders[1], status: OrderStatus.InDelivery });
        store.update(orders[2].id, { ...orders[2], status: OrderStatus.Sent });
      });

      it('should filter by customerId with exact match', () => {
        const result = OrderService.listOrders({ customerId: 'cust-a' });
        expect(result.total).toBe(2);
        expect(result.orders.every((o) => o.customerId === 'cust-a')).toBe(true);
      });

      it('should not match partial customerId strings', () => {
        const result = OrderService.listOrders({ customerId: 'cust' });
        expect(result.total).toBe(0);
      });

      it('should filter by multiple criteria simultaneously', () => {
        const result = OrderService.listOrders({
          customerId: 'cust-a',
          status: OrderStatus.Processing,
        });

        expect(result.total).toBe(1);
        expect(result.orders[0].customerId).toBe('cust-a');
        expect(result.orders[0].status).toBe(OrderStatus.Processing);
      });

      it('should respect pagination with filters', () => {
        const page1 = OrderService.listOrders({ limit: 1, offset: 0 });
        const page2 = OrderService.listOrders({ limit: 1, offset: 1 });
        const page3 = OrderService.listOrders({ limit: 1, offset: 2 });

        expect(page1.orders.length).toBe(1);
        expect(page2.orders.length).toBe(1);
        expect(page3.orders.length).toBe(1);
        expect(page1.total).toBe(3);
      });
    });

    describe('Idempotency - Repeated Operations', () => {
      it('should handle repeated valid status transitions idempotently', () => {
        const order = OrderService.createOrder('cust-1', ['item-1'], 'addr1');

        // Attempt same valid transition multiple times
        const result1 = OrderService.updateStatus(order.id, OrderStatus.Processing);
        const result2 = OrderService.updateStatus(order.id, OrderStatus.Processing);

        expect(result1?.status).toBe(OrderStatus.Processing);
        expect(result2?.status).toBe(OrderStatus.Processing);
      });

      it('should handle repeated invalid transitions idempotently', () => {
        const order = OrderService.createOrder('cust-1', ['item-1'], 'addr1');
        store.update(order.id, { ...order, status: OrderStatus.Sent });

        // Attempt same invalid transition multiple times
        const result1 = OrderService.updateStatus(order.id, OrderStatus.New);
        const result2 = OrderService.updateStatus(order.id, OrderStatus.New);
        const result3 = OrderService.updateStatus(order.id, OrderStatus.New);

        expect(result1?.status).toBe(OrderStatus.Sent);
        expect(result2?.status).toBe(OrderStatus.Sent);
        expect(result3?.status).toBe(OrderStatus.Sent);
      });

      it('should handle repeated payment updates', () => {
        const order = OrderService.createOrder('cust-1', ['item-1'], 'addr1');

        const payment1 = OrderService.updatePayment(order.id, 'pay-1');
        expect(payment1?.paymentId).toBe('pay-1');

        const payment2 = OrderService.updatePayment(order.id, 'pay-2');
        // payment2 should now reflect the latest payment
        expect(payment2?.paymentId).toBe('pay-2');

        const final = OrderService.getOrderById(order.id);
        expect(final?.paymentId).toBe('pay-2');
      });
    });

    describe('Isolation and State Management', () => {
      it('should not affect other orders when updating one', () => {
        const order1 = OrderService.createOrder('cust-1', ['item-1'], 'addr1');
        const order2 = OrderService.createOrder('cust-2', ['item-2'], 'addr2');

        OrderService.updateStatus(order1.id, OrderStatus.Processing);

        const updated1 = OrderService.getOrderById(order1.id);
        const unaffected2 = OrderService.getOrderById(order2.id);

        expect(updated1?.status).toBe(OrderStatus.Processing);
        expect(unaffected2?.status).toBe(OrderStatus.New);
      });

      it('should maintain order consistency across concurrent updates', () => {
        const order = OrderService.createOrder('cust-1', ['item-1'], 'addr1');

        // Simulate concurrent-like updates
        const payment = OrderService.updatePayment(order.id, 'pay-123');
        const status = OrderService.updateStatus(order.id, OrderStatus.Processing);
        const address = OrderService.updateOrder(order.id, {
          deliveryAddress: 'new-addr',
        });

        const final = OrderService.getOrderById(order.id);
        expect(final?.paid).toBe(true);
        expect(final?.paymentId).toBe('pay-123');
        expect(final?.status).toBe(OrderStatus.Processing);
        expect(final?.deliveryAddress).toBe('new-addr');
      });
    });
  });
});
