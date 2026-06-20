import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createStackNavigator } from "@react-navigation/stack";
import { Text } from "react-native";
import LoginScreen    from "./src/screens/Login";
import DashboardScreen from "./src/screens/Dashboard";
import VehiculesScreen from "./src/screens/Vehicules";
import BadgeScreen    from "./src/screens/Badge";
import AlertesScreen  from "./src/screens/Alertes";

const Tab   = createBottomTabNavigator();
const Stack = createStackNavigator();

function HomeTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        tabBarStyle: { backgroundColor: "#161b22", borderTopColor: "#30363d" },
        tabBarActiveTintColor: "#1a73e8",
        tabBarInactiveTintColor: "#8b949e",
        headerStyle: { backgroundColor: "#161b22" },
        headerTintColor: "#c9d1d9",
      }}>
      <Tab.Screen name="Dashboard"  component={DashboardScreen}
        options={{ title: "Accueil",   tabBarIcon: () => <Text>⬛</Text> }} />
      <Tab.Screen name="Vehicules"   component={VehiculesScreen}
        options={{ title: "Véhicules", tabBarIcon: () => <Text>🚗</Text> }} />
      <Tab.Screen name="Badge"       component={BadgeScreen}
        options={{ title: "Badgeage", tabBarIcon: () => <Text>📋</Text> }} />
      <Tab.Screen name="Alertes"     component={AlertesScreen}
        options={{ title: "Alertes",  tabBarIcon: () => <Text>🔔</Text> }} />
    </Tab.Navigator>
  );
}

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        <Stack.Screen name="Login" component={LoginScreen} />
        <Stack.Screen name="Home"  component={HomeTabs} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
