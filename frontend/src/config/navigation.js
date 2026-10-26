// Menu items for every role. The app shell builds the mobile bottom tabs
// and the desktop sidebar from this list.
// `tab: true` = shown in the mobile bottom bar (max 5).
// Hiding a menu item is NOT security: the backend checks the role on every request.
import {
  addCircleOutline,
  analyticsOutline,
  carOutline,
  cubeOutline,
  documentTextOutline,
  ellipsisHorizontal,
  flaskOutline,
  gitCompareOutline,
  gridOutline,
  homeOutline,
  listOutline,
  locateOutline,
  mapOutline,
  navigateOutline,
  peopleOutline,
  personCircleOutline,
  pricetagOutline,
  receiptOutline,
  syncOutline,
} from 'ionicons/icons'

export const ROLE_LABEL = Object.freeze({
  customer: 'Customer',
  dispatcher: 'Dispatcher',
  rider: 'Rider',
  owner: 'Owner',
})

/** Where each role lands after logging in. */
export const ROLE_HOME = Object.freeze({
  customer: '/customer/home',
  dispatcher: '/dispatcher/orders',
  rider: '/rider/trip',
  owner: '/owner/dashboard',
})

const more = (role) => ({ name: 'more', label: 'More', href: `/${role}/more`, icon: ellipsisHorizontal, tab: true, sidebar: false })

export const NAV = Object.freeze({
  customer: [
    { name: 'home', label: 'Home', href: '/customer/home', icon: homeOutline, tab: true },
    { name: 'order', label: 'Order water', href: '/customer/order', icon: addCircleOutline, tab: true },
    { name: 'orders', label: 'My orders', href: '/customer/orders', icon: receiptOutline, tab: true },
    { name: 'profile', label: 'Profile', href: '/customer/profile', icon: personCircleOutline, tab: true },
  ],
  dispatcher: [
    { name: 'orders', label: 'Orders', href: '/dispatcher/orders', icon: listOutline, tab: true },
    { name: 'plan', label: 'Plan deliveries', href: '/dispatcher/plan', icon: mapOutline, tab: true },
    { name: 'stock', label: 'Stock', href: '/dispatcher/stock', icon: cubeOutline, tab: true },
    { name: 'conflicts', label: 'Conflicts', href: '/dispatcher/conflicts', icon: gitCompareOutline, tab: true },
    more('dispatcher'),
  ],
  rider: [
    { name: 'trip', label: "Today's trip", href: '/rider/trip', icon: navigateOutline, tab: true },
    { name: 'sync', label: 'Sync status', href: '/rider/sync', icon: syncOutline, tab: true },
    more('rider'),
  ],
  owner: [
    { name: 'dashboard', label: 'Dashboard', href: '/owner/dashboard', icon: gridOutline, tab: true },
    { name: 'forecast', label: 'Forecasting', href: '/owner/forecast', icon: analyticsOutline, tab: true },
    { name: 'supplies', label: 'Stock & supplies', href: '/owner/supplies', icon: flaskOutline, tab: true },
    { name: 'reports', label: 'Reports', href: '/owner/reports', icon: documentTextOutline, tab: true },
    { name: 'users', label: 'Users', href: '/owner/users', icon: peopleOutline },
    { name: 'vehicles', label: 'Vehicles', href: '/owner/vehicles', icon: carOutline },
    { name: 'products', label: 'Products & prices', href: '/owner/products', icon: pricetagOutline },
    { name: 'service-area', label: 'Service area', href: '/owner/service-area', icon: locateOutline },
    more('owner'),
  ],
})
