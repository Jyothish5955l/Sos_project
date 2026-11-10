importScripts(
    "https://www.gstatic.com/firebasejs/12.3.0/firebase-app-compat.js"
);

importScripts(
    "https://www.gstatic.com/firebasejs/12.3.0/firebase-messaging-compat.js"
);


// ============================================================
// FIREBASE CONFIG
// ============================================================

firebase.initializeApp({

    apiKey: "YOUR_API_KEY",

    authDomain: "YOUR_PROJECT_ID.firebaseapp.com",

    projectId: "YOUR_PROJECT_ID",

    storageBucket: "YOUR_PROJECT_ID.firebasestorage.app",

    messagingSenderId: "YOUR_MESSAGING_SENDER_ID",

    appId: "YOUR_APP_ID"

});


const messaging =
    firebase.messaging();


// ============================================================
// BACKGROUND NOTIFICATION
// ============================================================

messaging.onBackgroundMessage(
    function(payload) {

        console.log(
            "[firebase-messaging-sw.js] Background message:",
            payload
        );


        const title =
            payload.notification?.title ||
            "SOS Guardian";


        const options = {

            body:
                payload.notification?.body ||
                "Emergency notification received.",

            icon: "/static/icon.png",

            badge: "/static/icon.png"

        };


        self.registration.showNotification(
            title,
            options
        );

    }
);