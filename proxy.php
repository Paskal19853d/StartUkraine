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
// Встановіть змінну середовища ALERTS_API_KEY на хостингу
// або покладіть ключ у файл proxy.key поруч з цим файлом (рядок без пробілів)
$_api_key = getenv('ALERTS_API_KEY');
if (!$_api_key) {
    $_key_file = __DIR__ . '/proxy.key';
    if (file_exists($_key_file)) {
        $_api_key = trim(file_get_contents($_key_file));
    }
}
if (!$_api_key) {
    http_response_code(500);
    echo json_encode(['error' => 'API key not configured']);
    exit;
}
define('API_KEY', $_api_key);
unset($_api_key, $_key_file);
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
