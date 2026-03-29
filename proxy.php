<?php
/**
 * proxy.php — alerts.in.ua API проксі
 * Завантаж на хостинг поруч з index.html
 * API ключ зберігається тут, не у HTML
 */

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Headers: *');
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-cache, max-age=0');

// ── API КЛЮЧ ──────────────────────────────────────────
define('API_KEY', '57fb756a020521fc83927919590c9addcef38d5fab2203');
// ─────────────────────────────────────────────────────

$type = $_GET['type'] ?? 'active';

$urls = [
    'active' => 'https://api.alerts.in.ua/v1/alerts/active.json',
    'iot'    => 'https://api.alerts.in.ua/v1/iot/active_air_raid_alerts_by_oblast.json',
];

if (!isset($urls[$type])) {
    http_response_code(400);
    echo json_encode(['error' => 'Unknown type']);
    exit;
}

$ch = curl_init($urls[$type]);
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT        => 8,
    CURLOPT_SSL_VERIFYPEER => true,
    CURLOPT_HTTPHEADER     => [
        'Authorization: Bearer ' . API_KEY,
        'X-API-Key: '            . API_KEY,
        'Accept: application/json',
        'User-Agent: UkraineAlertMap/1.0',
    ],
]);

$body   = curl_exec($ch);
$status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$err    = curl_error($ch);
curl_close($ch);

if ($err) {
    http_response_code(502);
    echo json_encode(['error' => $err]);
    exit;
}

http_response_code($status);
echo $body;
