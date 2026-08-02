import { OrderService } from "@/lib/service";
import { OrderStatus } from "@/lib/types";
import store from "@/lib/store";

describe("OrderService", () => {
  beforeEach(() => {
    store.clear();
  });

  afterEach(() => {
    store.clear();
  });

  describe("createOrder", () => {
    it("should create a new order with correct initial state", () => {
      const order = OrderService.createOrder(
        "cust-123",
        ["item-1", "item-2"],
        "123 Main St",
      );

      expect(order.id).toBeDefined();
      expect(order.customerId).toBe("cust-123");
      expect(order.orderedItems).toEqual(["item-1", "item-2"]);
      expect(order.deliveryAddress).toBe("123 Main St");
      expect(order.status).toBe(OrderStatus.New);
      expect(order.paid).toBe(false);
      expect(order.createdAt).toBeDefined();
      expect(order.deliveredAt).toBeUndefined();
      expect(order.paymentId).toBeUndefined();
    });
  });

  describe("listOrders - BUG-4: Status filtering", () => {
    beforeEach(() => {
      OrderService.createOrder("cust-1", ["i1"], "addr1");
      OrderService.createOrder("cust-2", ["i2"], "addr2");
      OrderService.createOrder("cust-3", ["i3"], "addr3");

      // Update statuses
      const orders = store.getAll();
      store.update(orders[0].id, {
        ...orders[0],
        status: OrderStatus.Processing,
      });
      store.update(orders[1].id, {
        ...orders[1],
        status: OrderStatus.InDelivery,
      });
      store.update(orders[2].id, { ...orders[2], status: OrderStatus.Sent });
    });

    it("should filter orders by exact status", () => {
      const result = OrderService.listOrders({
        status: OrderStatus.Processing,
      });

      expect(result.total).toBe(1);
      expect(result.orders[0].status).toBe(OrderStatus.Processing);
    });

    it('should filter orders by "In Delivery" status (exact match, not partial)', () => {
      const result = OrderService.listOrders({
        status: OrderStatus.InDelivery,
      });

      expect(result.total).toBe(1);
      expect(result.orders[0].status).toBe(OrderStatus.InDelivery);
    });

    it('should return all orders with status "Sent"', () => {
      const result = OrderService.listOrders({ status: OrderStatus.Sent });

      expect(result.total).toBe(1);
      expect(result.orders[0].status).toBe(OrderStatus.Sent);
    });

    it('should not match partial status strings (e.g., "In" should not match "In Delivery")', () => {
      const result = OrderService.listOrders({ status: "In" });

      // BUG-4: Current implementation uses loose == comparison
      // This should return 0 results for "In" but may match incorrectly
      expect(result.total).toBe(0);
    });
  });

  describe("listOrders - Customer filtering", () => {
    beforeEach(() => {
      OrderService.createOrder("cust-1", ["i1"], "addr1");
      OrderService.createOrder("cust-2", ["i2"], "addr2");
      OrderService.createOrder("cust-1", ["i3"], "addr3");
    });

    it("should filter orders by customerId", () => {
      const result = OrderService.listOrders({ customerId: "cust-1" });

      expect(result.total).toBe(2);
      expect(result.orders.every((o) => o.customerId === "cust-1")).toBe(true);
    });
  });

  describe("listOrders - Pagination", () => {
    beforeEach(() => {
      for (let i = 0; i < 15; i++) {
        OrderService.createOrder(`cust-${i}`, [`item-${i}`], `addr-${i}`);
      }
    });

    it("should apply limit correctly", () => {
      const result = OrderService.listOrders({ limit: 5 });

      expect(result.orders.length).toBe(5);
      expect(result.total).toBe(15);
    });

    it("should apply offset correctly", () => {
      const result1 = OrderService.listOrders({ limit: 5, offset: 0 });
      const result2 = OrderService.listOrders({ limit: 5, offset: 5 });

      expect(result1.orders[0].id).not.toBe(result2.orders[0].id);
    });
  });

  describe("updateStatus - BUG-3: No status transition validation", () => {
    it('should prevent transition from "Sent" to "Processing"', () => {
      const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
      store.update(order.id, { ...order, status: OrderStatus.Sent });

      const updated = OrderService.updateStatus(
        order.id,
        OrderStatus.Processing,
      );

      // BUG-3: Should reject this transition, but currently allows it
      expect(updated?.status).not.toBe(OrderStatus.Processing);
    });

    it('should prevent transition from "Sent" to "New"', () => {
      const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
      store.update(order.id, { ...order, status: OrderStatus.Sent });

      const updated = OrderService.updateStatus(order.id, OrderStatus.New);

      // BUG-3: Should reject this transition
      expect(updated?.status).not.toBe(OrderStatus.New);
    });

    it('should allow valid transition from "New" to "Processing"', () => {
      const order = OrderService.createOrder("cust-1", ["i1"], "addr1");

      const updated = OrderService.updateStatus(
        order.id,
        OrderStatus.Processing,
      );

      expect(updated?.status).toBe(OrderStatus.Processing);
    });

    it('should allow valid transition from "Processing" to "InDelivery"', () => {
      const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
      store.update(order.id, { ...order, status: OrderStatus.Processing });

      const updated = OrderService.updateStatus(
        order.id,
        OrderStatus.InDelivery,
      );

      expect(updated?.status).toBe(OrderStatus.InDelivery);
    });
  });

  describe("updatePayment", () => {
    it("should mark order as paid and set paymentId", () => {
      const order = OrderService.createOrder("cust-1", ["i1"], "addr1");

      const updated = OrderService.updatePayment(order.id, "pay-123");

      expect(updated?.paid).toBe(true);
      expect(updated?.paymentId).toBe("pay-123");
    });
  });

  describe("markDelivered", () => {
    it('should set deliveredAt and status to "Sent"', () => {
      const order = OrderService.createOrder("cust-1", ["i1"], "addr1");

      const updated = OrderService.markDelivered(order.id);

      expect(updated?.deliveredAt).toBeDefined();
      expect(updated?.status).toBe(OrderStatus.Sent);
    });
  });

  describe("deleteOrder", () => {
    it("should delete an order", () => {
      const order = OrderService.createOrder("cust-1", ["i1"], "addr1");

      const deleted = OrderService.deleteOrder(order.id);
      const fetched = OrderService.getOrderById(order.id);

      expect(deleted).toBe(true);
      expect(fetched).toBeUndefined();
    });

    it("should return false if order does not exist", () => {
      const deleted = OrderService.deleteOrder("nonexistent");

      expect(deleted).toBe(false);
    });
  });

  describe("State Machine Transitions - Enhanced FIRST Coverage", () => {
    describe("Valid Transitions (Happy Path)", () => {
      it("should allow all valid state transitions in sequence", () => {
        const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
        expect(order.status).toBe(OrderStatus.New);

        // New → Processing
        const step1 = OrderService.updateStatus(order.id, OrderStatus.Processing);
        expect(step1?.status).toBe(OrderStatus.Processing);

        // Processing → InDelivery
        const step2 = OrderService.updateStatus(order.id, OrderStatus.InDelivery);
        expect(step2?.status).toBe(OrderStatus.InDelivery);

        // InDelivery → Sent
        const step3 = OrderService.updateStatus(order.id, OrderStatus.Sent);
        expect(step3?.status).toBe(OrderStatus.Sent);
      });

      it("should allow New → Processing transition", () => {
        const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
        const updated = OrderService.updateStatus(order.id, OrderStatus.Processing);
        expect(updated?.status).toBe(OrderStatus.Processing);
      });

      it("should allow Processing → InDelivery transition", () => {
        const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
        store.update(order.id, { ...order, status: OrderStatus.Processing });
        const updated = OrderService.updateStatus(order.id, OrderStatus.InDelivery);
        expect(updated?.status).toBe(OrderStatus.InDelivery);
      });

      it("should allow InDelivery → Sent transition", () => {
        const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
        store.update(order.id, { ...order, status: OrderStatus.InDelivery });
        const updated = OrderService.updateStatus(order.id, OrderStatus.Sent);
        expect(updated?.status).toBe(OrderStatus.Sent);
      });
    });

    describe("Invalid Backward Transitions", () => {
      it("should prevent Sent → Processing backward transition", () => {
        const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
        store.update(order.id, { ...order, status: OrderStatus.Sent });
        const updated = OrderService.updateStatus(order.id, OrderStatus.Processing);
        expect(updated?.status).toBe(OrderStatus.Sent); // Status unchanged
      });

      it("should prevent Sent → InDelivery backward transition", () => {
        const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
        store.update(order.id, { ...order, status: OrderStatus.Sent });
        const updated = OrderService.updateStatus(order.id, OrderStatus.InDelivery);
        expect(updated?.status).toBe(OrderStatus.Sent); // Status unchanged
      });

      it("should prevent Sent → New backward transition", () => {
        const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
        store.update(order.id, { ...order, status: OrderStatus.Sent });
        const updated = OrderService.updateStatus(order.id, OrderStatus.New);
        expect(updated?.status).toBe(OrderStatus.Sent); // Status unchanged
      });

      it("should prevent InDelivery → New backward transition", () => {
        const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
        store.update(order.id, { ...order, status: OrderStatus.InDelivery });
        const updated = OrderService.updateStatus(order.id, OrderStatus.New);
        expect(updated?.status).toBe(OrderStatus.InDelivery); // Status unchanged
      });

      it("should prevent InDelivery → Processing backward transition", () => {
        const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
        store.update(order.id, { ...order, status: OrderStatus.InDelivery });
        const updated = OrderService.updateStatus(order.id, OrderStatus.Processing);
        expect(updated?.status).toBe(OrderStatus.InDelivery); // Status unchanged
      });

      it("should prevent Processing → New backward transition", () => {
        const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
        store.update(order.id, { ...order, status: OrderStatus.Processing });
        const updated = OrderService.updateStatus(order.id, OrderStatus.New);
        expect(updated?.status).toBe(OrderStatus.Processing); // Status unchanged
      });
    });

    describe("Invalid Skipped Transitions (Non-Sequential)", () => {
      it("should prevent New → InDelivery skip transition", () => {
        const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
        const updated = OrderService.updateStatus(order.id, OrderStatus.InDelivery);
        expect(updated?.status).toBe(OrderStatus.New); // Status unchanged
      });

      it("should prevent New → Sent skip transition", () => {
        const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
        const updated = OrderService.updateStatus(order.id, OrderStatus.Sent);
        expect(updated?.status).toBe(OrderStatus.New); // Status unchanged
      });

      it("should prevent Processing → Sent skip transition", () => {
        const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
        store.update(order.id, { ...order, status: OrderStatus.Processing });
        const updated = OrderService.updateStatus(order.id, OrderStatus.Sent);
        expect(updated?.status).toBe(OrderStatus.Processing); // Status unchanged
      });
    });

    describe("Terminal State Enforcement", () => {
      it("should prevent any transitions from Sent terminal state", () => {
        const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
        store.update(order.id, { ...order, status: OrderStatus.Sent });

        // Try all possible transitions from Sent
        const toProcessing = OrderService.updateStatus(order.id, OrderStatus.Processing);
        expect(toProcessing?.status).toBe(OrderStatus.Sent);

        const toInDelivery = OrderService.updateStatus(order.id, OrderStatus.InDelivery);
        expect(toInDelivery?.status).toBe(OrderStatus.Sent);

        const toNew = OrderService.updateStatus(order.id, OrderStatus.New);
        expect(toNew?.status).toBe(OrderStatus.Sent);

        // Attempting same status should also return unchanged
        const toSent = OrderService.updateStatus(order.id, OrderStatus.Sent);
        expect(toSent?.status).toBe(OrderStatus.Sent);
      });
    });

    describe("markDelivered - State Machine Integration", () => {
      it("should allow markDelivered to set Sent status from InDelivery", () => {
        const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
        store.update(order.id, { ...order, status: OrderStatus.InDelivery });

        const updated = OrderService.markDelivered(order.id);
        expect(updated?.status).toBe(OrderStatus.Sent);
        expect(updated?.deliveredAt).toBeDefined();
      });

      it("markDelivered should forcefully set status to Sent (bypasses state machine)", () => {
        const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
        // Note: markDelivered directly sets Sent, doesn't validate via updateStatus
        const updated = OrderService.markDelivered(order.id);
        expect(updated?.status).toBe(OrderStatus.Sent);
      });
    });
  });

  describe("Validation Error Handling - Enhanced FIRST Coverage", () => {
    describe("createOrder - Input Validation Errors", () => {
      it("should throw error for empty orderedItems array", () => {
        expect(() => {
          OrderService.createOrder("cust-1", [], "addr1");
        }).toThrow();
      });

      it("should throw error for non-string orderedItems elements", () => {
        expect(() => {
          OrderService.createOrder("cust-1", ["item1", 2 as any], "addr1");
        }).toThrow();
      });

      it("should throw error for empty deliveryAddress", () => {
        expect(() => {
          OrderService.createOrder("cust-1", ["item1"], "");
        }).toThrow();
      });

      it("should throw error for whitespace-only deliveryAddress", () => {
        expect(() => {
          OrderService.createOrder("cust-1", ["item1"], "   ");
        }).toThrow();
      });

      it("should throw error for empty customerId", () => {
        expect(() => {
          OrderService.createOrder("", ["item1"], "addr1");
        }).toThrow();
      });

      it("should throw error for whitespace-only customerId", () => {
        expect(() => {
          OrderService.createOrder("   ", ["item1"], "addr1");
        }).toThrow();
      });

      it("error message should be parseable JSON containing validation errors", () => {
        try {
          OrderService.createOrder("cust-1", [], "addr1");
        } catch (error) {
          const errorMessage = (error as Error).message;
          const errorObj = JSON.parse(errorMessage);
          expect(errorObj.orderedItems).toBeDefined();
        }
      });
    });
  });

  describe("updateOrder - State Machine Integration", () => {
    it("should reject invalid status transitions via updateOrder", () => {
      const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
      store.update(order.id, { ...order, status: OrderStatus.Sent });

      const updated = OrderService.updateOrder(order.id, { status: OrderStatus.Processing });

      // Status should not change
      expect(updated?.status).toBe(OrderStatus.Sent);
    });

    it("should allow valid status transitions via updateOrder", () => {
      const order = OrderService.createOrder("cust-1", ["i1"], "addr1");

      const updated = OrderService.updateOrder(order.id, { status: OrderStatus.Processing });

      expect(updated?.status).toBe(OrderStatus.Processing);
    });

    it("should update other fields even if status transition is invalid", () => {
      const order = OrderService.createOrder("cust-1", ["i1"], "addr1");
      store.update(order.id, { ...order, status: OrderStatus.Sent });

      const updated = OrderService.updateOrder(order.id, {
        status: OrderStatus.Processing, // Invalid
        deliveryAddress: "new-address",  // Valid
      });

      // Status should not change, but deliveryAddress should
      expect(updated?.status).toBe(OrderStatus.Sent);
      expect(updated?.deliveryAddress).toBe("new-address");
    });
  });

  describe("listOrders - Strict Equality Behavior", () => {
    beforeEach(() => {
      const o1 = OrderService.createOrder("cust-1", ["i1"], "addr1");
      const o2 = OrderService.createOrder("cust-2", ["i2"], "addr2");
      const o3 = OrderService.createOrder("cust-3", ["i3"], "addr3");

      store.update(o1.id, { ...o1, status: OrderStatus.Processing });
      store.update(o2.id, { ...o2, status: OrderStatus.InDelivery });
      store.update(o3.id, { ...o3, status: OrderStatus.Sent });
    });

    it("should use strict equality for exact status matching", () => {
      const result = OrderService.listOrders({ status: OrderStatus.Processing });
      expect(result.total).toBe(1);
      expect(result.orders[0].status).toBe(OrderStatus.Processing);
    });

    it("should not match partial status strings with strict equality", () => {
      const result = OrderService.listOrders({ status: "In" });
      expect(result.total).toBe(0);
    });

    it("should not match status with different casing", () => {
      const result = OrderService.listOrders({ status: "processing" as any });
      expect(result.total).toBe(0);
    });

    it("should match each status individually (no type coercion)", () => {
      const processing = OrderService.listOrders({ status: OrderStatus.Processing });
      const inDelivery = OrderService.listOrders({ status: OrderStatus.InDelivery });
      const sent = OrderService.listOrders({ status: OrderStatus.Sent });

      expect(processing.total).toBe(1);
      expect(inDelivery.total).toBe(1);
      expect(sent.total).toBe(1);
    });
  });
});
