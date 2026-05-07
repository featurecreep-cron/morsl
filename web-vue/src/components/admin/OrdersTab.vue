<template>
  <div id="panel-orders" role="tabpanel" aria-labelledby="tab-orders">

    <!-- Request Queue -->
    <section class="admin-section">
      <h2 class="section-title">
        Request Queue
        <span class="tab-badge" v-show="admin.orders.length > 0" style="margin-left:0.5rem;">{{ admin.orders.length }}</span>
      </h2>
      <div style="margin-bottom:0.75rem;">
        <button class="btn-generate btn-secondary" @click="admin.clearOrders()"
                :disabled="admin.orders.length === 0" style="height:30px; font-size:0.85rem;">
          Clear All Requests
        </button>
      </div>
      <div v-show="admin.orders.length === 0" class="tag-empty">No requests yet</div>
      <div class="diagnostics-list" style="max-height:400px; overflow-y:auto;">
        <div v-for="order in admin.orders" :key="order.id"
             class="constraint-chip order-row" style="justify-content:space-between;"
             @click="admin.viewOrderRecipe(order)">
          <span>
            <strong>{{ order.recipe_name }}</strong>
            <span class="order-user-name" v-show="order.customer_name">
              {{ ' \u2014 ' + (order.customer_name || '') }}
            </span>
            <small>{{ new Date(order.timestamp).toLocaleTimeString() }}</small>
          </span>
          <button class="btn-chip-remove" @click.stop="admin.markOrderReady(order)" title="Mark as ready" style="color:var(--accent-color); font-size:0.9rem;">&#10003;</button>
          <button class="btn-icon-danger" @click.stop="admin.deleteOrder(order)" title="Delete request">&times;</button>
        </div>
      </div>

      <!-- Order Counts Summary -->
      <div v-show="admin.orderCounts.length > 0" style="margin-top:0.75rem;">
        <h3 class="constraint-group-title">Totals</h3>
        <div v-for="oc in admin.orderCounts" :key="oc.recipe_id" class="constraint-chip">
          <strong>{{ oc.recipe_name }}</strong>
          <span>x{{ oc.count }}</span>
        </div>
      </div>
    </section>

  </div>
</template>

<script setup lang="ts">
import { useAdminStore } from '@/stores/admin'

const admin = useAdminStore()
</script>
